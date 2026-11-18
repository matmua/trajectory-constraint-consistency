"""Restore local AppWorld annotations with the upstream bundle format."""
from pathlib import Path
from appworld.common.constants import PASSWORD,SALT
from appworld.common.utils import unpack_bundle
if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    unpack_bundle(bundle_file_path=str(root/'appworld-annotations.bundle'),base_directory=str(root),password=PASSWORD,salt=SALT)
