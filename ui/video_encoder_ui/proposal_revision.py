from pathlib import Path

def review_montage_identification(*args, **kwargs):
    # Keep metadata/duration checks usable without loading the graphical browser.
    from .vidb_montage_review import review_montage_identification as review
    return review(*args, **kwargs)


def can_review_proposal(monitor):
    writer = getattr(monitor, 'trim_project_writer', None)
    result = getattr(writer, 'vidb_result', None) or {}
    if not isinstance(result, dict):
        return False
    return bool(result.get('selection_url') or result.get('review_url'))


def review_proposal(monitor):
    writer = getattr(monitor, 'trim_project_writer', None)
    session = getattr(monitor, 'trim_session', None)
    source = getattr(monitor, 'source_path', None)
    if writer is None or session is None or source is None:
        return False
    suggested = getattr(monitor, 'project_path', None)
    if suggested is None or Path(suggested).name == 'proposal.json':
        suggested = Path('/videos') / Path(source).with_suffix('.json').name
    accepted = review_montage_identification(monitor, session, source, suggested, writer)
    if accepted:
        monitor._runtime_reference = None
        monitor._proposal_revised = True
    return accepted


def revised_destination(monitor, current):
    from .catalogue_destination import suggested_film_output
    from .episode_destination import suggested_episode_output

    writer = getattr(monitor, 'trim_project_writer', None)
    result = getattr(writer, 'vidb_result', None) or {}
    metadata = result.get('metadata', {})
    if metadata.get('record_kind') == 'episode':
        return suggested_episode_output(metadata, current)
    if metadata.get('record_kind') == 'standalone_video':
        return suggested_film_output(metadata, current)
    return Path(current)


def choose_project_json(monitor, title, suggested):
    if can_review_proposal(monitor):
        from .project_destination import choose_project_output

        selected, _filter = choose_project_output(monitor, suggested)
        return selected
    from PySide6 import QtWidgets

    selected, _filter = QtWidgets.QFileDialog.getSaveFileName(
        monitor, title, str(suggested), "Projet video_encoder (*.json);;Tous les fichiers (*)")
    return selected
