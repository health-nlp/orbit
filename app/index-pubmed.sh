# Download raw PubMed data.
uv run -m pybool_ir.cli pubmed download -b baseline
# Convert the data into a single JSONL file.
uv run -m pybool_ir.cli pubmed process -b baseline -o pubmed-processed.jsonl
# Index the processed PubMed data.
uv run -m pybool_ir.cli pubmed index -b pubmed-processed.jsonl -s 1 -i index