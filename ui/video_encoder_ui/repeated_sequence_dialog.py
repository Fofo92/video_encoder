"""Experimental motif discovery and review, with cancellable child processes."""
import json
import hashlib
import os
from pathlib import Path
import signal
import sys
import uuid

from PySide6 import QtCore, QtGui, QtWidgets

from .repeated_sequence_review import check_source, inside_occurrences, proposed_session, adjust_review_boundary, latest_discovery, refinement_problem, support_family_problem, pair_problem, automatic_hypothesis, latest_extraction
from .graphic_review import observation_manifest, load_graphic_review, graphic_preview_rows


class RepeatedSequenceDialog(QtWidgets.QDialog):
    def __init__(self, source, bounds, frame_source, parent=None):
        super().__init__(parent)
        self.source, self.bounds, self.frame_source = Path(source), bounds, frame_source
        self.repository = Path(__file__).resolve().parents[2]
        self.report = self.report_path = self.refined = self.session = None
        self.observation_manifest = self.graphic_state = None
        self.displayed_frame = None
        self.busy = False
        self.task = self.output = None
        self.last_progress = ''
        self.preview_rows = []
        self.visible_candidates = []
        self.elapsed = QtCore.QElapsedTimer()
        self.clock = QtCore.QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self.update_task_status)
        self.progress_buffer = ''
        self.phase_label = ''
        self.source_progress = ''
        self.setWindowTitle('Séparateurs répétés — expérimental')
        self.resize(880, 720)
        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel('Prépare une hypothèse de coupures, puis contrôle chaque départ et chaque reprise. '
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
        self.copy_diagnostic = QtWidgets.QPushButton('Copier le chemin du dossier de diagnostic')
        self.copy_diagnostic.setVisible(False)
        self.copy_diagnostic.clicked.connect(self.copy_diagnostic_path)
        layout.addWidget(self.copy_diagnostic)
        self.stage = QtWidgets.QLabel()
        self.stage.setWordWrap(True)
        layout.addWidget(self.stage)
        self.activity = QtWidgets.QProgressBar()
        self.activity.setRange(0, 0)
        layout.addWidget(self.activity)
        self.groups = QtWidgets.QTableWidget(0, 4)
        self.groups.setHorizontalHeaderLabels(['Groupe', 'Occurrences totales', 'Dans l’œuvre', 'Durée médiane du noyau'])
        self.groups.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.groups.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.groups.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.groups.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.groups, 1)
        self.advanced = QtWidgets.QCheckBox('Vue avancée : afficher aussi les groupes non affinables')
        self.advanced.toggled.connect(self.render_groups)
        layout.addWidget(self.advanced)
        self.paired = QtWidgets.QCheckBox('Deux familles distinctes : départs et reprises')
        self.paired.toggled.connect(self.render_groups)
        layout.addWidget(self.paired)
        self.role_controls = QtWidgets.QWidget()
        roles = QtWidgets.QHBoxLayout(self.role_controls)
        roles.setContentsMargins(0, 0, 0, 0)
        self.departure_family = QtWidgets.QComboBox()
        self.resume_family = QtWidgets.QComboBox()
        for title, combo in [('Départs vers la publicité', self.departure_family), ('Reprises de l’œuvre', self.resume_family)]:
            roles.addWidget(QtWidgets.QLabel(title))
            roles.addWidget(combo, 1)
            combo.currentIndexChanged.connect(self.role_changed)
        layout.addWidget(self.role_controls)
        self.role_controls.setVisible(False)
        self.groups.itemSelectionChanged.connect(self.group_changed)
        preview_layout = QtWidgets.QHBoxLayout()
        self.hits = QtWidgets.QListWidget()
        preview_layout.addWidget(self.hits, 1)
        self.preview = QtWidgets.QLabel('Sélectionne une occurrence pour voir la source.')
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setWordWrap(True)
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
        self.nudge_buttons = []
        for label, step in [('−1 image', -1), ('+1 image', 1)]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(lambda _checked=False, delta=step: self.frame.setValue(self.frame.value() + delta))
            navigation.addWidget(button)
            self.nudge_buttons.append(button)
        layout.addLayout(navigation)
        self.adjust_button = QtWidgets.QPushButton('Retenir cette image pour le raccord')
        self.adjust_button.setToolTip('Enregistrer la limite affichée dans cette proposition. Confirme ensuite les raccords et remplace le montage pour les utiliser dans l’éditeur.')
        self.adjust_button.clicked.connect(self.adjust_boundary)
        layout.addWidget(self.adjust_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.confirm = QtWidgets.QCheckBox('Je confirme l’alternance : départ vers la publicité, puis reprise de l’œuvre.')
        self.confirm.setToolTip('Confirmer ce sens pour chaque paire d’occurrences avant de remplacer le montage.')
        self.confirm.setEnabled(False)
        self.confirm.toggled.connect(self.update_actions)
        layout.addWidget(self.confirm)
        bottom = QtWidgets.QHBoxLayout()
        self.refine_button = QtWidgets.QPushButton('Affiner le groupe sélectionné')
        self.apply_button = QtWidgets.QPushButton('Remplacer le montage')
        self.apply_button.setToolTip('Utiliser les segments contrôlés dans l’éditeur ; l’encodage reste une étape distincte.')
        self.cancel_button = QtWidgets.QPushButton('Fermer')
        bottom.addWidget(self.refine_button)
        bottom.addWidget(self.apply_button)
        bottom.addWidget(self.cancel_button)
        layout.addLayout(bottom)
        self.refine_button.clicked.connect(self.refine_group)
        self.apply_button.clicked.connect(self.apply_segments)
        self.cancel_button.clicked.connect(self.reject)
        self.expert = QtWidgets.QCheckBox('Réglages avancés : examiner et choisir les groupes')
        layout.insertWidget(5, self.expert)
        self.expert.toggled.connect(self.refresh_selection_mode)
        self.refresh_selection_mode()
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        self.group_process = hasattr(QtCore.QProcess.UnixProcessFlag, 'CreateNewSession') if hasattr(QtCore.QProcess, 'UnixProcessFlag') else False
        if self.group_process:
            parameters = QtCore.QProcess.UnixProcessParameters()
            parameters.flags = QtCore.QProcess.UnixProcessFlag.CreateNewSession
            self.process.setUnixProcessParameters(parameters)
        self.process.readyReadStandardOutput.connect(self.progress)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.update_actions()
        existing = latest_discovery(self.repository, self.source)
        if existing:
            self.load_report(existing)
        self.restore_completed_refinement()
        self.refresh_observations()
        self.update_actions()

    def refresh_observations(self):
        self.observation_manifest = observation_manifest(self.repository, self.source, self.bounds)

    def refresh_selection_mode(self):
        expert = self.expert.isChecked()
        for widget in [self.groups, self.advanced, self.paired]:
            widget.setVisible(expert)
        self.role_controls.setVisible(expert and self.paired.isChecked())
        if hasattr(self, 'process'):
            self.update_actions()
            self.update_discovery_notice()

    def update_discovery_notice(self):
        if self.busy or self.report is None or self.refined is not None or self.graphic_state is not None:
            return
        prefix = 'Recherche partielle : plafonds atteints. ' if self.report.get('index_limits_reached') else ''
        if self.expert.isChecked():
            self.notice.setText(prefix + f'{self.groups.rowCount()} groupes affichés sur '
                                f"{len(self.report['candidates'])}. Choisis une proposition à affiner.")
        else:
            self.notice.setText(prefix + 'Recherche terminée. Aucun découpage encore validé.')

    def update_actions(self):
        selected = self.groups.currentRow() >= 0
        for widget in [self.open_button, self.new_button, self.cache_button, self.groups, self.hits, self.advanced, self.paired, self.departure_family, self.resume_family, self.expert]:
            widget.setEnabled(not self.busy)
        for widget in [self.edge, self.frame, *self.nudge_buttons]:
            widget.setEnabled(not self.busy and bool(self.preview_rows))
        self.update_adjust_action()
        self.confirm.setEnabled(not self.busy and self.refined is not None)
        self.activity.setVisible(self.busy)
        if self.busy:
            self.update_task_status()
        elif self.refined is not None:
            self.stage.setText('Affinement terminé — contrôle maintenant les raccords, puis confirme leur sens.')
        else:
            self.stage.setText('Repères du scan approximatifs — affinement nécessaire avant validation.')
        self.refine_button.setText('Affiner les deux familles' if self.paired.isChecked() else 'Affiner le groupe sélectionné')
        ready = selected or self.paired.isChecked()
        problem = self.selected_group_problem() if ready else 'Choisis un groupe.'
        if not self.expert.isChecked():
            hypothesis, problem = automatic_hypothesis(self.report, *self.bounds)
            ready = hypothesis is not None
            bootstrap = (problem is not None and self.report_path is not None and self.report is not None
                         and 0 < len(self.report.get('candidates', [])) <= 100)
            if self.observation_manifest is not None:
                ready, problem = True, None
            elif bootstrap:
                ready, problem = True, None
            self.refine_button.setText('Préparer les raccords à contrôler')
            if not self.busy and self.refined is None:
                self.stage.setText('Des extraits sont disponibles : la recherche graphique et la préparation des raccords seront enchaînées.'
                                   if self.observation_manifest is not None else
                                   'Des propositions restent ambiguës : prépare les extraits d’observation, puis la recherche graphique, sans choisir de groupe.'
                                   if bootstrap else problem or (
                    f"Hypothèse prioritaire : {hypothesis['breaks']} plage(s) possible(s), à vérifier. "
                    f"{hypothesis['alternatives']} autre(s) hypothèse(s). "
                    'Les limites seront calculées avant validation.'))
        if not self.busy and self.graphic_state is not None:
            self.stage.setText('Raccords préparés — contrôle les images conservées et écartées avant confirmation.'
                               if self.graphic_state == 'ready_for_review' else
                               'Préparation terminée avec des cas non résolus : le montage reste inchangé.')
        self.refine_button.setEnabled(not self.busy and ready and problem is None)
        self.refine_button.setToolTip(problem or (
            'Réutiliser les extraits pour analyser l’enregistrement et préparer les raccords.'
            if self.observation_manifest is not None and not self.expert.isChecked() else
            'Extraire les fenêtres et affiner les limites du motif.'))
        self.apply_button.setEnabled(not self.busy and self.refined is not None and self.confirm.isChecked())
        self.cancel_button.setText('Interrompre et fermer' if self.busy else 'Fermer')
        if not self.busy and not self.preview_rows:
            self.preview.clear()
            self.preview.setText(self.stage.text())

    def update_task_status(self):
        if self.busy:
            seconds = max(0, self.elapsed.elapsed() // 1000) if self.elapsed.isValid() else 0
            minutes, seconds = divmod(seconds, 60)
            self.stage.setText(f'Calcul en cours — {self.phase_label} — écoulé {minutes:02d}:{seconds:02d}. '
                               + (self.source_progress + '. ' if self.source_progress else '') +
                               'Contrôle des raccords disponible à la fin.')

    def selected_candidate_index(self):
        row = self.groups.currentRow()
        return self.visible_candidates[row] if 0 <= row < len(self.visible_candidates) else -1

    def selected_group_problem(self):
        if self.paired.isChecked():
            return pair_problem(self.report, self.departure_family.currentData(), self.resume_family.currentData(), *self.bounds)
        index = self.selected_candidate_index()
        if self.report is None or index < 0:
            return 'Choisis un groupe.'
        return refinement_problem(inside_occurrences(self.report['candidates'][index], *self.bounds))

    def new_workspace(self):
        return self.repository / 'tmp' / 'repeated-sequence-reviews' / uuid.uuid4().hex

    def start(self, task, script, arguments, output):
        if self.busy:
            return
        self.clear_refinement()
        self.copy_diagnostic.setVisible(False)
        self.task, self.output, self.busy = task, output, True
        self.preview_rows = []
        self.hits.clear()
        self.last_progress = ''
        self.progress_buffer = ''
        self.source_progress = ''
        self.phase_label = ('Analyse graphique et préparation des raccords' if task == 'graphic' else
                            'Lecture et extraction de la source' if task == 'refinement' else 'Découverte des répétitions')
        self.elapsed.start()
        self.clock.start()
        self.activity.setRange(0, 3 if task == 'refinement' else 0)
        self.activity.setValue(0)
        self.activity.setFormat('Préparation…')
        self.preview.clear()
        self.preview.setText('Calcul en cours… L’aperçu des raccords sera disponible à la fin.')
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
        if self.report_path is not None:
            manifest = self.report_path.parent / 'manifest.json'
            try:
                if json.loads(manifest.read_text()).get('status') == 'completed':
                    self.discover(self.report_path.parent)
                    return
            except (OSError, ValueError):
                pass
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choisir le dossier du cache de découverte', str(self.repository / 'tmp'))
        if directory:
            self.discover(Path(directory))

    def open_results(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Ouvrir un résultat de découverte', str(self.repository / 'tmp'), 'Rapports JSON (*.json)')
        if path:
            self.load_report(Path(path))

    def load_report(self, path):
        self.output = path.parent
        try:
            report = json.loads(path.read_text())
            if path.name == 'pipeline.json' or report.get('review_origin') in ('graphic_hypotheses','format_hypotheses'):
                self.display_graphic_review(path if path.name == 'pipeline.json' else path.parent / 'pipeline.json')
                return
            if 'source_motif_limits' in report:
                self.display_refinement(report)
                return
            check_source(report, self.source)
            if report.get('sample_fps') != 5 or not isinstance(report.get('candidates'), list):
                raise ValueError('Choisis le fichier resultat.json d’une découverte sans modèle.')
            for candidate in report['candidates']:
                inside_occurrences(candidate, *self.bounds)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))
            return
        self.report, self.report_path = report, path
        self.render_groups()
        self.refresh_observations()
        self.update_actions()

    def render_groups(self):
        self.groups.setRowCount(0)
        self.visible_candidates = []
        self.clear_refinement()
        self.role_controls.setVisible(self.expert.isChecked() and self.paired.isChecked())
        for combo in [self.departure_family, self.resume_family]:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem('Choisir…', None)
        if self.report is None:
            for combo in [self.departure_family, self.resume_family]:
                combo.blockSignals(False)
            return
        for index, candidate in enumerate(self.report['candidates']):
            if support_family_problem(candidate, *self.bounds) is None:
                count = len(inside_occurrences(candidate, *self.bounds))
                for combo in [self.departure_family, self.resume_family]:
                    combo.addItem(f'Groupe {index + 1} — {count} dans l’œuvre', index + 1)
        for combo in [self.departure_family, self.resume_family]:
            combo.blockSignals(False)
        total = len(self.report['candidates'])
        for index, candidate in enumerate(self.report['candidates']):
            inside = inside_occurrences(candidate, *self.bounds)
            problem = (support_family_problem(candidate, *self.bounds) if self.paired.isChecked()
                       else refinement_problem(inside))
            if problem and not self.advanced.isChecked():
                continue
            row = self.groups.rowCount()
            self.visible_candidates.append(index)
            self.groups.insertRow(row)
            durations = sorted(item['core_end_seconds'] - item['core_start_seconds'] for item in candidate['occurrences'])
            median = durations[len(durations) // 2] if durations else 0
            values = [str(index + 1), str(len(candidate['occurrences'])), str(len(inside)), f'{median:.2f} s']
            for column, value in enumerate(values):
                self.groups.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        self.update_actions()
        self.update_discovery_notice()

    def role_changed(self):
        self.clear_refinement()
        self.notice.setText(self.selected_group_problem() or 'Deux familles choisies : affine-les puis contrôle les raccords.')
        self.update_actions()

    def clear_refinement(self):
        self.partial_refined = None
        self.refined = None
        self.graphic_state = None
        self.confirm.setChecked(False)
        self.confirm.setEnabled(False)

    def group_changed(self):
        self.clear_refinement()
        index = self.selected_candidate_index()
        self.preview_rows = []
        if self.report is not None and 0 <= index < len(self.report['candidates']):
            self.preview_rows = [{'start': round(row['core_start_seconds'] * 25),
                                  'end': round(row['core_end_seconds'] * 25), 'approximate': True}
                                 for row in inside_occurrences(self.report['candidates'][index], *self.bounds)]
        self.populate_hits()
        if index >= 0:
            problem = self.selected_group_problem()
            prefix = 'Recherche partielle : plafonds atteints. ' if self.report.get('index_limits_reached') else ''
            self.notice.setText(prefix + (problem or ('Examine les occurrences, puis affine les deux familles choisies.'
                                                  if self.paired.isChecked() else 'Examine les occurrences, puis affine le groupe sélectionné.')))
        self.update_actions()

    def populate_hits(self):
        self.hits.clear()
        adjusted={row['index'] for row in (self.refined or getattr(self,'partial_refined',None) or {}).get('manual_adjustments',[])}
        for index, row in enumerate(self.preview_rows):
            hours, remainder = divmod(row['start'] // 25, 3600)
            minutes, seconds = divmod(remainder, 60)
            departure = row.get('candidate_role', 'departure' if index % 2 == 0 else 'resume') == 'departure'
            number = row.get('group_index', index // 2 + 1)
            role = f'Départ proposé {number}' if departure else f'Reprise proposée {number}'
            text = f'{index + 1} — {hours:02d}:{minutes:02d}:{seconds:02d}' if row.get('approximate') else role
            text += ' (ajusté)' if row.get('report_index',index) in adjusted else ' (approximatif)' if row.get('approximate') else ' (affiné)'
            item = QtWidgets.QListWidgetItem(text)
            item.setToolTip(f"Image conservée : {row['kept_frame']} ; image écartée : {row['excluded_frame']}"
                           if 'kept_frame' in row else f"Images : {row['start']}–{row['end']} (fin exclusive)")
            self.hits.addItem(item)
        if self.preview_rows:
            self.hits.setCurrentRow(0)

    def show_occurrence(self, index):
        if self.busy:
            return
        if 0 <= index < len(self.preview_rows):
            row = self.preview_rows[index]
            if self.refined is not None or 'kept_frame' in row:
                departure = row.get('candidate_role', 'departure' if index % 2 == 0 else 'resume') == 'departure'
                labels = (['Dernière image conservée (OUT)', 'Première image écartée'] if departure else
                          ['Dernière image écartée', 'Première image conservée (IN)'])
                if self.edge.itemText(0) != labels[0]:
                    self.edge.blockSignals(True)
                    self.edge.clear()
                    self.edge.addItems(labels)
                    self.edge.setCurrentIndex(0 if departure else 1)
                    self.edge.blockSignals(False)
                if 'kept_frame' in row:
                    positions = ([row['kept_frame'], row['excluded_frame']] if departure else
                                 [row['excluded_frame'], row['kept_frame']])
                else:
                    positions = [row['start'] - 1, row['start']] if departure else [row['end'] - 1, row['end']]
                position = positions[self.edge.currentIndex()]
            else:
                if self.edge.itemText(0) != 'Début du motif':
                    self.edge.blockSignals(True)
                    self.edge.clear()
                    self.edge.addItems(['Début du motif', 'Fin exclusive du motif'])
                    self.edge.blockSignals(False)
                position = row['end'] if self.edge.currentIndex() else row['start']
            blocker=QtCore.QSignalBlocker(self.frame)
            self.frame.setValue(min(self.frame.maximum(), max(0, position)))
            del blocker
            self.show_frame(self.frame.value())
        self.update_adjust_action()

    def update_adjust_action(self):
        if hasattr(self,'adjust_button'):
            reason=('Attends la fin de la préparation.' if self.busy else
                    'Prépare des raccords avant d’ajuster une limite.' if self.refined is None and getattr(self,'partial_refined',None) is None else
                    'Sélectionne un départ ou une reprise à ajuster.' if not 0<=self.hits.currentRow()<len(self.preview_rows) else
                    'Affiche une image valide avant de retenir cette limite.' if self.displayed_frame!=self.frame.value() else None)
            self.adjust_button.setEnabled(reason is None)
            self.adjust_button.setToolTip(reason or 'Retenir l’image affichée comme limite du raccord. Confirme ensuite les raccords et remplace le montage pour les utiliser dans l’éditeur.')

    def adjust_boundary(self):
        report=self.refined or getattr(self,'partial_refined',None)
        if self.busy or report is None or self.displayed_frame!=self.frame.value():
            return
        visible_index=self.hits.currentRow();edge=self.edge.currentIndex()
        if not 0<=visible_index<len(self.preview_rows):return
        index=self.preview_rows[visible_index].get('report_index',visible_index)
        try:
            edited=adjust_review_boundary(report,self.source,*self.bounds,index,self.frame.value(),edge)
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.notice.setText(str(error))
            QtWidgets.QMessageBox.warning(self,'Ajustement du raccord',str(error))
            return
        if self.refined is None:self.partial_refined=edited
        else:self.refined=edited
        self.session=None
        self.confirm.setChecked(False)
        if edited.get('review_origin') in ('graphic_hypotheses','format_hypotheses'):
            self.preview_rows=graphic_preview_rows(edited,*self.bounds)
        else:
            self.preview_rows=[{'start':row['motif_start_decoded_frame'],'end':row['motif_end_decoded_frame_exclusive']}
                               for row in edited['source_motif_limits']]
        self.populate_hits();self.hits.setCurrentRow(visible_index);self.edge.setCurrentIndex(edge)
        self.notice.setText('Raccord ajusté. Des cas restent non résolus ; le montage ne peut pas encore être remplacé.'
                            if self.refined is None else
                            'Raccord ajusté. Contrôle les images, confirme les raccords puis clique sur « Remplacer le montage ».')
        self.update_actions()

    def show_frame(self, position):
        if self.busy:
            return
        self.displayed_frame=None
        try:
            def read(target):
                image,actual,_=self.frame_source.frame_at(target)
                if type(actual) is not int or not 0<=actual<self.frame_source.length or image.isNull():
                    raise ValueError('Le lecteur n’a pas fourni d’image avec une position valide.')
                return image,actual
            image,actual=read(position)
            if actual!=position:
                # One bounded correction handles a consistent seek offset.
                # If exact seeking is unavailable, retain the known displayed
                # coordinate, as the main editor does, rather than a stale frame.
                corrected=2*position-actual
                if 0<=corrected<self.frame_source.length:
                    try:
                        other_image,other_actual=read(corrected)
                        if abs(other_actual-position)<abs(actual-position):
                            image,actual=other_image,other_actual
                    except Exception:
                        pass  # The first image still has a valid known position.
            self.preview.setPixmap(QtGui.QPixmap.fromImage(image).scaled(440, 248, QtCore.Qt.AspectRatioMode.KeepAspectRatio))
            self.preview.setToolTip(f'Image affichée : {actual} ; demandée : {position}. Les positions avant affinement sont approximatives.')
            blocker=QtCore.QSignalBlocker(self.frame)
            self.frame.setValue(actual)
            del blocker
            self.displayed_frame=actual
        except Exception as error:
            self.preview.setText(f'Aperçu indisponible : {error}')
        self.update_adjust_action()

    def refine_group(self):
        if self.busy:
            return
        self.refresh_observations()
        if not self.expert.isChecked() and self.observation_manifest is not None:
            self.start_graphic_review()
            return
        if not self.expert.isChecked():
            hypothesis, problem = automatic_hypothesis(self.report, *self.bounds)
            if problem:
                if self.report_path is not None and self.report is not None and 0 < len(self.report.get('candidates', [])) <= 100:
                    self.start_graphic_review(discovery_report=self.report_path)
                    return
                self.notice.setText(problem)
                return
            choice = (['--candidate', str(hypothesis['candidate'])] if 'candidate' in hypothesis else
                      ['--departure-candidate', str(hypothesis['departure']),
                       '--resume-candidate', str(hypothesis['resume'])])
        elif self.selected_group_problem():
            return
        else:
            choice = (['--departure-candidate', str(self.departure_family.currentData()),
                       '--resume-candidate', str(self.resume_family.currentData())] if self.paired.isChecked()
                      else ['--candidate', str(self.selected_candidate_index() + 1)])
        self.clear_refinement()
        output = self.new_workspace()
        previous = latest_extraction(self.repository, self.source, self.bounds, self.report_path, choice)
        reuse = ['--reuse-extraction', str(previous)] if previous else []
        self.start('refinement', 'refine_source_occurrences.py',
                   [*reuse, '--scan-report', str(self.report_path), *choice,
                    '--start-frame', str(self.bounds[0]), '--end-frame', str(self.bounds[1]), '--output', str(output)], output)

    def start_graphic_review(self, discovery_report=None):
        if self.busy or (self.observation_manifest is None and discovery_report is None):
            return
        output = self.new_workspace()
        observation_input = (['--discovery-report', str(discovery_report)] if discovery_report is not None else
                             ['--observation-manifest', str(self.observation_manifest)])
        self.start('graphic', 'prepare_graphic_review.py',
                   ['--source', str(self.source), *observation_input,
                    '--in-frame', str(self.bounds[0]), '--out-frame', str(self.bounds[1]), '--output', str(output)], output)

    def progress(self):
        message = bytes(self.process.readAllStandardOutput()).decode(errors='replace')
        if message:
            self.last_progress = message[-1500:]
            self.progress_buffer += message
            lines = self.progress_buffer.split('\n')
            self.progress_buffer = lines.pop()
            for line in lines:
                if line.startswith('REVIEW_STAGE '):
                    try:
                        value = json.loads(line[len('REVIEW_STAGE '):])
                        total = value.get('total', 3)
                        if type(total) is int and 1 <= value['step'] <= total <= 5:
                            self.activity.setRange(0, total)
                            self.activity.setValue(value['step'] - 1)
                            self.activity.setFormat(f"Étape {value['step']}/{total} — {value['label']}")
                            self.phase_label = value['label']
                            self.source_progress = ''
                            self.update_task_status()
                    except (ValueError, KeyError, TypeError):
                        pass
                elif line.startswith('REVIEW_PROGRESS ') and self.task == 'graphic':
                    try:
                        value = json.loads(line[len('REVIEW_PROGRESS '):])
                        if 'sampled_seconds' in value:
                            seconds = value['sampled_seconds']
                            if type(seconds) not in (int, float) or not 0 <= seconds <= 21600:
                                continue
                            hours, rest = divmod(int(seconds), 3600)
                            minutes, seconds = divmod(rest, 60)
                            self.source_progress = f'Vidéo analysée : {hours:02d}:{minutes:02d}:{seconds:02d}'
                        elif type(value.get('decoded_frame')) is int and value['decoded_frame'] >= 0:
                            self.source_progress = f"Lecture jusqu’à l’image {value['decoded_frame']}"
                        self.update_task_status()
                    except (ValueError, KeyError, TypeError, OverflowError):
                        pass
            self.notice.setText(self.phase_label if self.task == 'graphic' or message.startswith('REVIEW_STAGE ') else
                                message.splitlines()[-1][-200:])

    def process_finished(self, code, status):
        if not self.busy:
            return
        self.progress()
        self.busy = False
        self.clock.stop()
        self.update_actions()
        if code != 0 or status != QtCore.QProcess.ExitStatus.NormalExit:
            if self.task == 'refinement' and not self.expert.isChecked() and status == QtCore.QProcess.ExitStatus.NormalExit:
                self.refresh_observations()
                if self.observation_manifest is not None:
                    self.start_graphic_review()
                    return
            self.error(f'Opération interrompue ou échouée. Dossier de travail : {self.output}\n{self.last_progress}')
            return
        if self.task == 'discovery':
            self.load_report(self.output / 'resultat.json')
            return
        try:
            if self.task == 'graphic':
                self.display_graphic_review(self.output / 'pipeline.json')
                return
            refined = json.loads((self.output / 'manifest.json').read_text())
            self.display_refinement(refined)
            self.refresh_observations()
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))

    def restore_completed_refinement(self):
        root = self.repository / 'tmp' / 'repeated-sequence-reviews'
        paths = sorted([*root.glob('*/manifest.json'), *root.glob('*/pipeline.json')],
                       key=lambda path: path.stat().st_mtime_ns, reverse=True)
        for path in paths:
            try:
                if path.name == 'pipeline.json':
                    self.display_graphic_review(path)
                    self.notice.setText('Préparation graphique retrouvée sur disque. Aucun nouveau calcul lancé ; contrôle les raccords disponibles.')
                    return
                refined = json.loads(path.read_text())
                proposed_session(refined, self.source, *self.bounds, confirmed=True)
                self.display_refinement(refined)
                self.output = path.parent
                self.notice.setText(('Repères graphiques expérimentaux retrouvés. ' if
                                     refined.get('refinement', {}).get('graphic_fallback_used') else
                                     'Affinement terminé retrouvé sur disque. ') +
                                    'Contrôle les raccords ; aucun nouveau calcul n’a été lancé.')
                return
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def display_graphic_review(self, path):
        pipeline, report = load_graphic_review(path, self.source, self.bounds)
        self.clear_refinement()
        self.output = path.parent
        self.graphic_state = pipeline['status']
        self.refined = report if pipeline['status'] == 'ready_for_review' else None
        self.partial_refined = report if pipeline['status'] == 'needs_review' else None
        self.preview_rows = graphic_preview_rows(report, *self.bounds) if report is not None else []
        self.populate_hits()
        self.copy_diagnostic.setVisible(True)
        self.copy_diagnostic.setToolTip(str(self.output.resolve()))
        self.notice.setText('Préparation terminée. Contrôle chaque départ et chaque reprise avant confirmation.'
                            if self.refined is not None else
                            'Préparation terminée avec des cas non résolus. ' +
                            pipeline.get('reason', 'Les raccords incomplets restent à examiner.'))
        reused = ('Scan réutilisé. ' if pipeline.get('reused_scan_from') else '')
        reused += ('Extraits natifs réutilisés. ' if pipeline.get('reused_review_from') else '')
        if reused:
            self.notice.setText(reused + self.notice.text())
        self.update_actions()

    def display_refinement(self, refined):
        # Geometric validation does not replace the unchecked semantic confirmation.
        session = proposed_session(refined, self.source, *self.bounds, confirmed=True)
        roles = refined.get('selected_families')
        if roles:
            self.paired.setChecked(True)
            if self.report_path is not None and hashlib.sha256(self.report_path.read_bytes()).hexdigest() == refined.get('scan_report_sha256'):
                for combo, role in [(self.departure_family, 'departure'), (self.resume_family, 'resume')]:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(max(0, combo.findData(roles[role])))
                    combo.blockSignals(False)
        self.clear_refinement()
        self.refined = refined
        self.preview_rows = [{'start': row['motif_start_decoded_frame'], 'end': row['motif_end_decoded_frame_exclusive']}
                             for row in refined['source_motif_limits']]
        self.populate_hits()
        self.confirm.setEnabled(True)
        self.notice.setText(('Repères graphiques expérimentaux : vérifie chaque raccord. ' if
                             refined.get('refinement', {}).get('graphic_fallback_used') else '') +
                            f'{len(session.segments)} segments possibles si tu confirmes l’alternance départ/reprise. '
                            'Contrôle les images autour des limites avant de charger le montage.')
        self.update_actions()

    def process_error(self, error):
        if self.busy and error == QtCore.QProcess.ProcessError.FailedToStart:
            self.busy = False
            self.clock.stop()
            self.update_actions()
            self.error(self.process.errorString())

    def apply_segments(self):
        try:
            self.session = proposed_session(self.refined, self.source, *self.bounds, confirmed=self.confirm.isChecked())
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.error(str(error))
            return
        self.accept()

    def copy_diagnostic_path(self):
        if self.output is not None:
            QtWidgets.QApplication.clipboard().setText(str(self.output.resolve()))

    def error(self, message):
        self.clear_refinement()
        self.preview_rows = []
        self.hits.clear()
        self.update_actions()
        summary = str(message).strip().splitlines()[-1] if str(message).strip() else 'Opération impossible.'
        summary = summary[:240]
        self.notice.setText(summary)
        if not self.busy:
            self.preview.setText('Opération terminée sans nouvelle proposition. ' + summary)
        self.copy_diagnostic.setVisible(self.output is not None)
        self.copy_diagnostic.setToolTip(str(self.output.resolve()) if self.output is not None else '')
        QtWidgets.QMessageBox.warning(self, 'Séparateurs répétés', summary)

    def reject(self):
        if self.busy:
            self.busy = False
            self.clock.stop()
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
