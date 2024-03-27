"""
Merges all text files in a directory into a single markdown file.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

import fire
from cleantext import clean
from natsort import natsorted
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DROP_WORDS = [
    "summary",
    "output",
    "nougat",
    "mp3",
    "OCR",
    "ocr",
]


def process2words(input_string):
    # Replace multiple underscores with a single underscore
    processed_string = re.sub(r"_+", "_", input_string)
    # Replace underscores with a space
    processed_string = processed_string.replace("_", " ").replace("-", " ")

    # drop words
    processed_string = " ".join(
        [word for word in processed_string.split() if word not in DROP_WORDS]
    )

    # replace/remove random artifacts that should not be there like %! etc

    return re.sub(r"\s+", " ", processed_string).strip()


def merge_text_files(
    input_dir: str = r"C:\Users\Tommaso\Documents\Dev\Abstractions\abstractions\goap",
    output_dir: str = None,
    file_extension: str = ".py",
    fancy: bool = False,
    keybert_model: str = "avsolatorio/GIST-small-Embedding-v0",
    recursive: bool = True,
    add_fences: bool = False,
    min_chars: int = None,
):
    """
    Merges all text files in a directory into a single markdown file.
        If fancy_filename is True, generates a filename based on the top keywords.

    Args:
        input_dir (str): The directory containing the text files to be merged.
        output_dir (str): Optional; the directory where the merged markdown file will be saved. Defaults to the parent directory of input_dir.
        file_extension (str): Optional; the file extension of the text files to be merged. Defaults to ".txt".
        fancy_filename (bool): Optional; flag to enable generating a filename based on content keywords. Defaults to False.
    """

    input_dir = Path(input_dir).resolve()
    output_dir = Path(output_dir) if output_dir else input_dir.parent.parent.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    file_extension = file_extension.strip(".")
    logger.info(
        f"Searching for {file_extension} files in {input_dir}, recursive={recursive}..."
    )
    files = (
        list(input_dir.rglob(f"*.{file_extension}"))
        if recursive
        else list(input_dir.glob(f"*.{file_extension}"))
    )

    aggregated_content = ""
    logger.info(f"Merging {len(files)} files...")
    for file in tqdm(natsorted(files), desc="Processing files", unit="files"):
        if file.is_file() and file.stat().st_mode & 0o400:  # Check if file is readable
            with file.open("r", encoding="utf-8") as f:
                file_content = f.read()

            if min_chars is not None and len(file_content.strip()) < min_chars:
                logger.warning(
                    f"Skipping {file} because it has less than {min_chars} characters."
                )
                continue
            if add_fences:
                file_content = f"```{file_extension}\n{file_content}\n```"
            aggregated_content += (
                f"## {process2words(file.stem)}\n\n{file_content}\n\n---\n\n"
            )
        else:
            logger.error(f"{file} is either not a file or not readable.")

    # Decide filename based on fancy_filename flag
    base_name = input_dir.name
    if fancy:
        logger.info(f"Generating filename based on top 3 kw ({keybert_model})...")
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer

        embedmodel = SentenceTransformer(
            keybert_model,
            revision="main",
            trust_remote_code=True,
        )  # other models to try: "nomic-ai/nomic-embed-text-v1", "jinaai/jina-embeddings-v2-small-en"
        # embedmodel.max_seq_length = 8192
        keywords = KeyBERT(model=embedmodel).extract_keywords(
            aggregated_content[:5000],
            stop_words="english",
            top_n=3,
            use_mmr=True,
            diversity=0.8,
        )
        keywords_str = " ".join([keyword[0] for keyword in keywords])
        print(keywords_str)
        keywords_str = clean(
            keywords_str,
            lower=False,
            no_line_breaks=True,
            no_punct=True,
        ).replace(" ", "_")
        keywords_str = re.sub(r"_+", "_", keywords_str)
        output_file_name = f"Merged_Text-{keywords_str}.md"
    else:
        output_file_name = f"Merged_Text-{base_name}.md"
    output_file = output_dir / output_file_name

    if output_file.exists():
        overwrite = input(
            f"Output file {output_file} already exists. Overwrite? (y/n):"
        )
        if not overwrite.lower().startswith("y"):
            logger.info("Operation cancelled by user.")
            return

    with output_file.open("w", encoding="utf-8") as f:
        f.write(f"# Combined Text Dir from {base_name}\n\n")
        f.write(f"- Full filepath to the merged directory: `{input_dir}`\n\n")
        f.write(f"- Created: `{datetime.now().isoformat()}`\n\n")
        f.write(aggregated_content)

    logger.info(f"Merged files saved to:\n\t{output_file}")


if __name__ == "__main__":
    fire.Fire(merge_text_files)
