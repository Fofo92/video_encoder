"""Prepare whole DVD titles for the existing queue and vidb receipt workflow."""
import json
import os
import signal
import sys
import uuid
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from .dvd_import import (audio_defaults, new_project, provisional_output, subtitle_default, write_new)
from .trim_export_queue_client import TrimExportQueueError

PIPELINE = Path(__file__).resolve().parents[2] / 'lib/video_encoder/dvd_pipeline.py'


def helper(parent, label, *arguments, module=None):
    """A separate process group allows cancellation without leaving a copy running."""
    process = QtCore.QProcess(parent)
    process.setProgram('setsid')
    entry = ['-m', module] if module else [str(PIPELINE)]
    if module:
        process.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))
    process.setArguments([sys.executable, *entry, *map(str, arguments)])
    progress = QtWidgets.QProgressDialog(label, 'Annuler', 0, 0, parent)
    progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    loop = QtCore.QEventLoop()
    output, errors = bytearray(), bytearray()
    canceled = False

    def read():
        output.extend(bytes(process.readAllStandardOutput()))
        errors.extend(bytes(process.readAllStandardError()))
        del errors[:-16000]

    def cancel():
        nonlocal canceled
        canceled = True
        pid = process.processId()
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            def force_stop():
                if process.state() != QtCore.QProcess.ProcessState.NotRunning:
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            QtCore.QTimer.singleShot(3000, process, force_stop)

    progress.canceled.connect(cancel)
    process.readyReadStandardOutput.connect(read)
    process.readyReadStandardError.connect(read)
    process.finished.connect(loop.quit)
    process.errorOccurred.connect(lambda _error: loop.quit()
                                 if process.state() == QtCore.QProcess.ProcessState.NotRunning else None)
    process.start()
    if process.state() != QtCore.QProcess.ProcessState.NotRunning:
        loop.exec()
    read()
    progress.canceled.disconnect(cancel)
    progress.close()
    failed = process.exitStatus() != QtCore.QProcess.ExitStatus.NormalExit or process.exitCode() != 0
    message = errors.decode('utf-8', errors='replace').strip() or process.errorString()
    process.deleteLater()
    if canceled:
        raise ValueError('Opération annulée. Les copies locales déjà terminées sont conservées.')
    if failed:
        raise ValueError(message)
    return json.loads(output.decode('utf-8'))


def track_label(row):
    tags = row.get('tags', {})
    disposition = row.get('disposition', {})
    label = f"Piste {row['index']} · {tags.get('language', 'und')} · {row.get('codec_name', '')}"
    if tags.get('title'):
        label += f" · {tags['title']}"
    if disposition.get('hearing_impaired'):
        label += ' · malentendants'
    if disposition.get('visual_impaired'):
        label += ' · audiodescription'
    if 'nb_read_packets' in row:
        label += f" · {row['nb_read_packets']} paquets"
    return label


def choose_tracks(parent, copied):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle('Confirmer les pistes du titre DVD')
    layout = QtWidgets.QFormLayout(dialog)
    information = QtWidgets.QLabel(
        'Choisis la VF et/ou la VO, puis une piste de sous-titres français.\n'
        'L’ordre des pistes ne permet pas de reconnaître les sous-titres malentendants.\n'
        'Le nombre de paquets aide à distinguer une piste complète d’une piste presque vide.')
    information.setWordWrap(True)
    layout.addRow(information)
    rows = copied['probe']['streams']
    audio = [row for row in rows if row['codec_type'] == 'audio']
    subtitles = [row for row in rows if row['codec_type'] == 'subtitle']
    french, original = audio_defaults(audio)
    combos = []
    for label, candidates, default in (('Audio VF', audio, french), ('Audio VO', audio, original),
                                        ('Sous-titres', subtitles, subtitle_default(subtitles))):
        combo = QtWidgets.QComboBox()
        combo.addItem('Aucune', None)
        for row in candidates:
            combo.addItem(track_label(row), row['index'])
        if default is not None:
            combo.setCurrentIndex(combo.findData(default))
        layout.addRow(label, combo)
        combos.append(combo)
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                         | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    selected = [{'index': combo.currentData(), 'role': role}
                for combo, role in zip(combos[:2], ('french', 'original')) if combo.currentData() is not None]
    if not selected or len({row['index'] for row in selected}) != len(selected):
        raise ValueError('Sélectionne au moins une piste audio, sans sélectionner deux fois la même.')
    subtitle = combos[2].currentData()
    return selected, [subtitle] if subtitle is not None else []


def identify_destination(parent, document, suggested, record_id=None):
    from .catalogue_destination import suggested_film_output
    from .episode_destination import suggested_episode_output
    from .vidb_export_review import await_vidb_identification
    from .vidb_project_link import VidbProjectLink

    link = VidbProjectLink()
    provisional = suggested.with_suffix('.json')
    refresh = lambda: link.identify(document, provisional, refresh=True)
    if record_id is None:
        result = refresh()
    else:
        from .dvd_menu import bind_episode

        result = bind_episode(document, provisional, record_id)
    if result.get('status') != 'identified':
        if result.get('status') == 'disabled':
            raise ValueError('Configure la connexion vidb de video_encoder avant de préparer ce DVD.')
        result = await_vidb_identification(parent, result, refresh)
    if result is None:
        return None
    if result.get('status') != 'identified':
        raise ValueError('Le rattachement vidb doit être confirmé avant l’ajout à la file.')
    metadata = result.get('metadata', {})
    kind = metadata.get('record_kind')
    if kind == 'episode':
        destination = suggested_episode_output(metadata, suggested)
    elif kind == 'standalone_video':
        destination = suggested_film_output(metadata, suggested)
    else:
        raise ValueError('Choisis une fiche d’épisode ou d’œuvre autonome dans vidb.')
    document['vidb'] = result
    return destination


def save_and_enqueue(parent, document, destination, client):
    answer = QtWidgets.QMessageBox.question(
        parent, 'Confirmer le titre DVD et sa destination',
        f"Fiche vidb : {document['vidb'].get('record_title', document['vidb']['record_id'])}\n\n"
        f"Destination :\n{destination}\n\n"
        'Vérifie que cette fiche correspond au titre du disque sélectionné.\n'
        'Ajouter à la file ? Si elle est déjà lancée, ce titre sera encodé à son tour.',
        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        QtWidgets.QMessageBox.StandardButton.No)
    if answer != QtWidgets.QMessageBox.StandardButton.Yes:
        return False
    if os.path.lexists(destination):
        raise ValueError(f'La sortie existe déjà : {destination}')
    project = destination.with_suffix('.json')
    write_new(project, document)
    try:
        client.enqueue(project, destination)
    except TrimExportQueueError as error:
        raise ValueError(f'{error}\n\nProjet conservé : {project}\n'
                         'Projets → Ouvrir un projet permet de reprendre l’ajout à la file.') from error
    return True


class DvdImportDialog(QtWidgets.QDialog):
    def __init__(self, parent, client):
        super().__init__(parent)
        self.client = client
        self.menu_selection = None
        self.menu_episodes = {}
        self.setWindowTitle('Préparer un DVD pour la file d’encodage')
        self.setMinimumWidth(640)
        layout = QtWidgets.QFormLayout(self)
        self.device = QtWidgets.QLineEdit('/dev/sr0')
        layout.addRow('Lecteur', self.device)
        scan = QtWidgets.QPushButton('Analyser le disque')
        scan.clicked.connect(self.scan)
        layout.addRow(scan)
        menu = QtWidgets.QPushButton('Reprendre un DVD préparé dans vidb…')
        menu.clicked.connect(self.identify_menu)
        layout.addRow(menu)
        self.titles = QtWidgets.QComboBox()
        self.titles.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.titles.activated.connect(self.use_menu_episode)
        layout.addRow('Titre DVD', self.titles)
        self.title = QtWidgets.QLineEdit()
        layout.addRow('Titre de l’œuvre ou de la série', self.title)
        self.episodic = QtWidgets.QCheckBox('Ce titre correspond à un épisode de série')
        layout.addRow(self.episodic)
        self.season, self.episode = QtWidgets.QSpinBox(), QtWidgets.QSpinBox()
        self.season.setRange(0, 99)
        self.season.setValue(1)
        self.episode.setRange(1, 999)
        layout.addRow('Saison', self.season)
        layout.addRow('Épisode', self.episode)
        self.season.setEnabled(False)
        self.episode.setEnabled(False)
        self.episodic.toggled.connect(self.season.setEnabled)
        self.episodic.toggled.connect(self.episode.setEnabled)
        help_text = QtWidgets.QLabel('Le numéro de titre DVD ne garantit pas l’ordre des épisodes. '
                                    'Vérifie chaque correspondance avec vidb. La copie locale sera conservée '
                                    'en cas d’annulation ou d’échec ; aucun état « possédé » ne sera changé ici.')
        help_text.setWordWrap(True)
        layout.addRow(help_text)
        self.copy_label = QtWidgets.QLabel()
        self.copy_label.setWordWrap(True)
        self.copy_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addRow(self.copy_label)
        self.prepare_button = QtWidgets.QPushButton('Copier, identifier et ajouter à la file')
        self.prepare_button.clicked.connect(self.prepare)
        layout.addRow(self.prepare_button)
        resume = QtWidgets.QPushButton('Reprendre une copie locale déjà terminée…')
        resume.clicked.connect(self.resume)
        layout.addRow(resume)
        close = QtWidgets.QPushButton('Fermer')
        close.clicked.connect(self.accept)
        layout.addRow(close)

    def scan(self):
        self.menu_selection = None
        self.menu_episodes.clear()
        try:
            device = self.device.text().strip()
            titles = helper(self, 'Analyse des titres DVD…', 'scan', device)
            self.titles.clear()
            for title in titles:
                duration = round(title['duration'])
                self.titles.addItem(f"Titre {title['title']} · {duration // 60} min {duration % 60:02d} s",
                                    dict(title, device=device))
            return bool(titles)
        except (OSError, ValueError, KeyError, TypeError) as error:
            QtWidgets.QMessageBox.warning(self, 'Analyse DVD impossible', str(error))
            return False

    def identify_menu(self):
        try:
            preparation = self.choose_dvd_preparation()
            if preparation is None:
                return
            if not preparation['series_ready']:
                raise ValueError(f"Associe la préparation n° {preparation['id']} à sa série dans DVD à préparer.")
            device = self.device.text().strip()
            if not self.scan():
                return
            result = helper(self, 'Lecture du menu du DVD préparé…', device, '--preparation-id', preparation['id'],
                            module='video_encoder_ui.dvd_menu')
            self.show_menu_episodes(result)
        except (OSError, ValueError, KeyError, TypeError) as error:
            QtWidgets.QMessageBox.warning(self, 'Identification du menu impossible', str(error))

    def choose_dvd_preparation(self):
        result = helper(self, 'Chargement des préparations DVD…', '--list-preparations',
                        module='video_encoder_ui.dvd_menu')
        choices = {}
        for row in result['preparations']:
            state = 'série associée' if row['series_ready'] else 'série à associer'
            count = f" · {row['announced_count']} contenus annoncés" if row['announced_count'] else ''
            choices[f"{row['title']}{count} · {state} · préparation n° {row['id']}"] = row
        if not choices:
            raise ValueError('Scanne d’abord le coffret dans DVD à préparer, puis reprends sa préparation ici.')
        choice, accepted = QtWidgets.QInputDialog.getItem(
            self, 'Reprendre une préparation', 'Choisis le coffret du disque inséré.',
            list(choices), 0, False)
        return choices[choice] if accepted else None

    def show_menu_episodes(self, result):
        title_indexes = {self.titles.itemData(i)['title']: i for i in range(self.titles.count())}
        choices = {}
        for row in result['episodes']:
            number = row['dvd_title']
            if number not in title_indexes or not 0 <= row['season'] <= 99 or not 1 <= row['episode'] <= 999:
                continue
            label = row['french_title'] or row['original_title']
            key = f"Titre {number} · S{row['season']:02d} E{row['episode']:02d} · {label}"
            choices[key] = row
        if not choices:
            raise ValueError('Aucun des titres proposés ne figure dans l’analyse du disque.')
        self.menu_episodes = {row['dvd_title']: (result['series_title'], row) for row in choices.values()}
        for label, row in choices.items():
            self.titles.setItemText(title_indexes[row['dvd_title']], label)
        indexes = [title_indexes[number] for number in self.menu_episodes]
        index = self.titles.currentIndex()
        if index not in indexes:
            index = min(indexes)
            self.titles.setCurrentIndex(index)
        self.use_menu_episode(index)

    def use_menu_episode(self, index):
        previous = self.menu_selection
        self.menu_selection = None
        item = self.titles.itemData(index)
        match = self.menu_episodes.get(item['title']) if item else None
        if match:
            series, row = match
            self.title.setText(series)
            self.episodic.setChecked(True)
            self.season.setValue(row['season'])
            self.episode.setValue(row['episode'])
            self.menu_selection = (self.menu_fields(), row['record_id'])
        elif previous:
            self.title.clear()

    def menu_fields(self):
        return (self.device.text().strip(), self.titles.currentIndex(), self.title.text(),
                self.episodic.isChecked(), self.season.value(), self.episode.value())

    def selected_menu_record_id(self):
        if self.menu_selection and self.menu_selection[0] == self.menu_fields():
            return self.menu_selection[1]
        return None

    def prepare(self):
        try:
            title = self.titles.currentData()
            if title is None:
                raise ValueError('Analyse le disque et choisis un titre.')
            provisional_output(self.title.text(), self.episodic.isChecked(), self.season.value(), self.episode.value())
            if title['device'] != self.device.text().strip():
                raise ValueError('Le lecteur a changé : analyse de nouveau le disque.')
            record_id = self.selected_menu_record_id()
            directory = Path('/commun/to_be_cut/DVD') / str(uuid.uuid4())
            copied = helper(self, 'Copie locale du titre DVD et inspection des pistes…', 'copy',
                            title['device'], title['title'], directory, title['duration'])
            if record_id is not None:
                series, episode = self.menu_episodes[title['title']]
                copied['menu_episode'] = {
                    'record_id': record_id, 'series': series, 'season': episode['season'], 'episode': episode['episode']
                }
            write_new(directory / 'dvd-source.json', copied)
            self.finish_copy(copied)
        except (OSError, ValueError, KeyError, TypeError) as error:
            QtWidgets.QMessageBox.warning(self, 'Titre DVD non ajouté', str(error))

    def resume(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Copie locale à reprendre',
                                                       '/commun/to_be_cut/DVD', 'Copie DVD (dvd-source.json)')
        if not path:
            return
        try:
            self.finish_copy(json.loads(Path(path).read_text(encoding='utf-8')))
        except (OSError, ValueError, KeyError, TypeError) as error:
            QtWidgets.QMessageBox.warning(self, 'Copie DVD non ajoutée', str(error))

    def finish_copy(self, copied):
        self.copy_label.setText(f"Copie locale conservée : {copied['path']}")
        selected = choose_tracks(self, copied)
        if selected is None:
            QtWidgets.QMessageBox.information(self, 'Copie locale conservée', copied['path'])
            return
        document = new_project(copied, *selected)
        episode = copied.get('menu_episode')
        if episode is None:
            suggested = provisional_output(self.title.text(), self.episodic.isChecked(),
                                            self.season.value(), self.episode.value())
            record_id = None
        else:
            suggested = provisional_output(episode['series'], True, episode['season'], episode['episode'])
            record_id = episode['record_id']
        destination = identify_destination(self, document, suggested, record_id=record_id)
        if destination is None:
            return
        if save_and_enqueue(self, document, destination, self.client):
            QtWidgets.QMessageBox.information(self, 'Titre DVD ajouté',
                f'{destination}\n\nLa file reste dans son état actuel. '
                'Tu peux préparer un autre titre ; le lecteur sera libre après sa copie.')


def reopen_dvd_project(parent, path, client):
    try:
        document = json.loads(Path(path).read_text(encoding='utf-8'))
        output = Path(path).with_suffix('.mkv')
        jobs = client.list_jobs()
        if any(Path(job['input_path']).absolute() == Path(path).absolute()
               and job['status'] in {'queued', 'running', 'deferred'} for job in jobs):
            QtWidgets.QMessageBox.information(parent, 'Projet DVD déjà en file',
                                              'Utilise Tâche → Modifier pour ajuster sa destination.')
            return
        if os.path.lexists(output):
            raise ValueError(f'La sortie existe déjà : {output}')
        if QtWidgets.QMessageBox.question(parent, 'Reprendre le projet DVD', f'Ajouter à la file ?\n{output}') \
                == QtWidgets.QMessageBox.StandardButton.Yes:
            client.enqueue(path, output)
    except (OSError, ValueError, KeyError, TypeError, TrimExportQueueError) as error:
        QtWidgets.QMessageBox.warning(parent, 'Projet DVD non ajouté', str(error))
