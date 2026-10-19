"""Experimental motif discovery and review, with cancellable child processes."""
import json
import os
from pathlib import Path
import signal
import sys
import uuid

from PySide6 import QtCore, QtGui, QtWidgets

from .repeated_sequence_review import check_source, inside_occurrences, proposed_session, latest_discovery, refinement_problem


class RepeatedSequenceDialog(QtWidgets.QDialog):
    def __init__(self, source, bounds, frame_source, parent=None):
        super().__init__(parent)
        self.source, self.bounds, self.frame_source = Path(source), bounds, frame_source
        self.repository = Path(__file__).resolve().parents[2]
        self.report = self.report_path = self.refined = self.session = None
        self.busy = False
        self.task = self.output = None
        self.last_progress = ''
        self.preview_rows = []
        self.setWindowTitle('Séparateurs répétés — expérimental')
        self.resize(880, 720)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel('Choisis un motif, vérifie ses occurrences, puis affine les limites. '
                                'Une répétition ne suffit pas à identifier une publicité.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        actions = QtWidgets.QHBoxLayout()
        self.open_button = QtWidgets.QPushButton('Ouvrir des résultats…')
        self.new_button = QtWidgets.QPushButton('Nouvelle recherche')
        self.cache_button = QtWidgets.QPushButton('Rechercher depuis un cache…')
        for button in [self.open_button, self.new_button, self.cache_button]:
            actions.addWidget(button)
        layout.addLayout(actions)
        self.open_button.clicked.connect(self.open_results)
        self.new_button.clicked.connect(lambda: self.discover())
        self.cache_button.clicked.connect(self.discover_from_cache)
        self.notice = QtWidgets.QLabel('Aucune recherche chargée.')
        self.notice.setWordWrap(True)
        self.notice.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.notice.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
        self.notice.setMaximumHeight(64)
        layout.addWidget(self.notice)
        self.groups = QtWidgets.QTableWidget(0, 4)
        self.groups.setHorizontalHeaderLabels(['Groupe', 'Occurrences totales', 'Dans l’œuvre', 'Durée médiane du noyau'])
        self.groups.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.groups.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.groups.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.groups.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.groups, 1)
        self.groups.itemSelectionChanged.connect(self.group_changed)
        preview_layout = QtWidgets.QHBoxLayout()
        self.hits = QtWidgets.QListWidget()
        preview_layout.addWidget(self.hits, 1)
        self.preview = QtWidgets.QLabel('Sélectionne une occurrence pour voir la source.')
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 180)
        preview_layout.addWidget(self.preview, 2)
        layout.addLayout(preview_layout, 2)
        self.hits.currentRowChanged.connect(self.show_occurrence)
        navigation = QtWidgets.QHBoxLayout()
        self.edge = QtWidgets.QComboBox()
        self.edge.addItems(['Début du motif', 'Fin exclusive du motif'])
        self.edge.currentIndexChanged.connect(lambda: self.show_occurrence(self.hits.currentRow()))
        navigation.addWidget(self.edge)
        navigation.addWidget(QtWidgets.QLabel('Image source :'))
        self.frame = QtWidgets.QSpinBox()
        self.frame.setRange(0, frame_source.length - 1)
        self.frame.valueChanged.connect(self.show_frame)
        navigation.addWidget(self.frame)
        for label, step in [('−1 image', -1), ('+1 image', 1)]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, delta=step: self.frame.setValue(self.frame.value() + delta))
            navigation.addWidget(button)
        layout.addLayout(navigation)
        self.confirm = QtWidgets.QCheckBox('Je confirme l’alternance : départ vers la publicité, puis reprise de l’œuvre.')
        self.confirm.setToolTip('Confirmer ce sens pour chaque paire d’occurrences avant de remplacer le montage.')
        self.confirm.setEnabled(False)
        self.confirm.toggled.connect(self.update_actions)
        layout.addWidget(self.confirm)
        bottom = QtWidgets.QHBoxLayout()
        self.refine_button = QtWidgets.QPushButton('Affiner le groupe sélectionné')
        self.apply_button = QtWidgets.QPushButton('Remplacer le montage par ces segments à contrôler')
        self.cancel_button = QtWidgets.QPushButton('Fermer')
        bottom.addWidget(self.refine_button)
        bottom.addWidget(self.apply_button)
        bottom.addWidget(self.cancel_button)
        layout.addLayout(bottom)
        self.refine_button.clicked.connect(self.refine_group)
        self.apply_button.clicked.connect(self.apply_segments)
        self.cancel_button.clicked.connect(self.reject)
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        self.group_process = hasattr(QtCore.QProcess.UnixProcessFlag, 'CreateNewSession') if hasattr(QtCore.QProcess, 'UnixProcessFlag') else False
        if self.group_process:
            parameters = QtCore.QProcess.UnixProcessParameters()
            parameters.flags = QtCore.QProcess.UnixProcessFlag.CreateNewSession
            self.process.setUnixProcessParameters(parameters)
        self.process.readyReadStandardOutput.connect(self.progress)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.update_actions()
        existing = latest_discovery(self.repository, self.source)
        if existing:
            self.load_report(existing)

    def update_actions(self):
        selected = self.groups.currentRow() >= 0
        for widget in [self.open_button, self.new_button, self.cache_button, self.groups, self.hits]:
            widget.setEnabled(not self.busy)
        problem = self.selected_group_problem() if selected else 'Choisis un groupe.'
        self.refine_button.setEnabled(not self.busy and selected and problem is None)
        self.refine_button.setToolTip(problem or 'Extraire les fenêtres et affiner les limites du motif.')
        self.apply_button.setEnabled(not self.busy and self.refined is not None and self.confirm.isChecked())
        self.cancel_button.setText('Interrompre et fermer' if self.busy else 'Fermer')

    def selected_group_problem(self):
        index = self.groups.currentRow()
        if self.report is None or index < 0:
            return 'Choisis un groupe.'
        return refinement_problem(inside_occurrences(self.report['candidates'][index], *self.bounds))

    def new_workspace(self):
        return self.repository / 'tmp' / 'repeated-sequence-reviews' / uuid.uuid4().hex

    def start(self, task, script, arguments, output):
        if self.busy:
            return
        self.clear_refinement()
        self.task, self.output, self.busy = task, output, True
        self.last_progress = ''
        self.update_actions()
        self.notice.setText('Recherche en cours…' if task == 'discovery' else 'Extraction et affinement en cours…')
        self.process.start(sys.executable, [str(self.repository / 'script' / 'research' / script), *arguments])

    def discover(self, cache=None):
        output = self.new_workspace()
        args = ['--source', str(self.source), '--output', str(output)]
        if cache:
            args += ['--reuse-cache', str(cache)]
        self.start('discovery', 'discover_source_sequences.py', args, output)

    def discover_from_cache(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choisir le dossier du cache de découverte', str(self.repository / 'tmp'))
        if directory:
            self.discover(Path(directory))

    def open_results(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Ouvrir un résultat de découverte', str(self.repository / 'tmp'), 'Rapports JSON (*.json)')
        if path:
            self.load_report(Path(path))

    def load_report(self, path):
        try:
            report = json.loads(path.read_text())
            check_source(report, self.source)
            if report.get('sample_fps') != 5 or not isinstance(report.get('candidates'), list):
                raise ValueError('Choisis le fichier resultat.json d’une découverte sans modèle.')
            rows = []
            for candidate in report['candidates']:
                inside = inside_occurrences(candidate, *self.bounds)
                durations = sorted(row['core_end_seconds'] - row['core_start_seconds'] for row in candidate['occurrences'])
                rows.append((len(candidate['occurrences']), len(inside), durations[len(durations) // 2] if durations else 0))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))
            return
        self.report, self.report_path = report, path
        self.groups.setRowCount(0)
        self.clear_refinement()
        for index, (total, inside, duration) in enumerate(rows):
            self.groups.insertRow(index)
            for column, value in enumerate([str(index + 1), str(total), str(inside), f'{duration:.2f} s']):
                self.groups.setItem(index, column, QtWidgets.QTableWidgetItem(value))
        self.notice.setText(('Recherche partielle : plafonds atteints. ' if report.get('index_limits_reached') else '') +
                            f'{len(rows)} groupes. Choisis le motif à examiner ; aucun groupe n’est sélectionné automatiquement.')
        self.update_actions()

    def clear_refinement(self):
        self.refined = None
        self.confirm.setChecked(False)
        self.confirm.setEnabled(False)

    def group_changed(self):
        self.clear_refinement()
        index = self.groups.currentRow()
        self.preview_rows = []
        if self.report is not None and 0 <= index < len(self.report['candidates']):
            self.preview_rows = [{'start': round(row['core_start_seconds'] * 25),
                                  'end': round(row['core_end_seconds'] * 25), 'approximate': True}
                                 for row in inside_occurrences(self.report['candidates'][index], *self.bounds)]
        self.populate_hits()
        if index >= 0:
            problem = self.selected_group_problem()
            prefix = 'Recherche partielle : plafonds atteints. ' if self.report.get('index_limits_reached') else ''
            self.notice.setText(prefix + (problem or 'Examine les occurrences, puis affine le groupe sélectionné.'))
        self.update_actions()

    def populate_hits(self):
        self.hits.clear()
        for index, row in enumerate(self.preview_rows):
            hours, remainder = divmod(row['start'] // 25, 3600)
            minutes, seconds = divmod(remainder, 60)
            text = f'{index + 1} — {hours:02d}:{minutes:02d}:{seconds:02d}'
            text += ' (approximatif)' if row.get('approximate') else ' (affiné)'
            item = QtWidgets.QListWidgetItem(text)
            item.setToolTip(f"Images : {row['start']}–{row['end']} (fin exclusive)")
            self.hits.addItem(item)
        if self.preview_rows:
            self.hits.setCurrentRow(0)

    def show_occurrence(self, index):
        if 0 <= index < len(self.preview_rows):
            row = self.preview_rows[index]
            position = row['end'] if self.edge.currentIndex() else row['start']
            self.frame.setValue(min(self.frame.maximum(), max(0, position)))
            self.show_frame(self.frame.value())

    def show_frame(self, position):
        try:
            image, actual, _ = self.frame_source.frame_at(position)
            self.preview.setPixmap(QtGui.QPixmap.fromImage(image).scaled(440, 248, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            self.preview.setToolTip(f'Image affichée : {actual}. Les positions avant affinement sont approximatives.')
        except Exception as error:
            self.preview.setText(f'Aperçu indisponible : {error}')

    def refine_group(self):
        if self.groups.currentRow() < 0 or self.busy or self.selected_group_problem():
            return
        self.clear_refinement()
        output = self.new_workspace()
        self.start('refinement', 'refine_source_occurrences.py',
                   ['--scan-report', str(self.report_path), '--candidate', str(self.groups.currentRow() + 1),
                    '--start-frame', str(self.bounds[0]), '--end-frame', str(self.bounds[1]), '--output', str(output)], output)

    def progress(self):
        message = bytes(self.process.readAllStandardOutput()).decode(errors='replace').strip()
        if message:
            self.last_progress = message[-1500:]
            self.notice.setText(message.splitlines()[-1][-200:])

    def finished(self, code, status):
        if not self.busy:
            return
        self.progress()
        self.busy = False
        self.update_actions()
        if code != 0 or status != QtCore.QProcess.ExitStatus.NormalExit:
            self.error(f'Opération interrompue ou échouée. Dossier de travail : {self.output}\n{self.last_progress}')
            return
        if self.task == 'discovery':
            self.load_report(self.output / 'resultat.json')
            return
        try:
            refined = json.loads((self.output / 'manifest.json').read_text())
            # Validate geometry before offering the explicit semantic confirmation.
            session = proposed_session(refined, self.source, *self.bounds, confirmed=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))
            return
        self.refined = refined
        self.preview_rows = [{'start': row['motif_start_decoded_frame'], 'end': row['motif_end_decoded_frame_exclusive']}
                             for row in refined['source_motif_limits']]
        self.populate_hits()
        self.confirm.setEnabled(True)
        self.notice.setText(f'{len(session.segments)} segments possibles si tu confirmes l’alternance départ/reprise. '
                            'Contrôle les images autour des limites avant de charger le montage.')
        self.update_actions()

    def process_error(self, error):
        if self.busy and error == QtCore.QProcess.ProcessError.FailedToStart:
            self.busy = False
            self.update_actions()
            self.error(self.process.errorString())

    def apply_segments(self):
        try:
            self.session = proposed_session(self.refined, self.source, *self.bounds, confirmed=self.confirm.isChecked())
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))
            return
        self.accept()

    def error(self, message):
        self.clear_refinement()
        self.update_actions()
        summary = str(message).strip().splitlines()[-1] if str(message).strip() else 'Opération impossible.'
        summary = summary[:240]
        self.notice.setText(summary)
        QtWidgets.QMessageBox.warning(self, 'Séparateurs répétés', summary)

    def reject(self):
        if self.busy:
            self.busy = False
            pid = self.process.processId()
            if self.group_process and pid:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                self.process.terminate()
            if not self.process.waitForFinished(1500):
                if self.group_process and pid:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    self.process.kill()
                self.process.waitForFinished(1500)
        super().reject()
