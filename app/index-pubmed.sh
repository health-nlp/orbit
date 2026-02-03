DOWNLOAD_TARGET=${DOWNLOAD_TARGET:-"baseline"}
RUN_MODE=${MODE:-"full"}
echo "----------------------------------------"
echo "MODE: $RUN_MODE"
echo "DOWNLOAD TARGET: $DOWNLOAD_TARGET"

if [ -d index ] && [ "$(ls -A index)" ]; then
  echo ">>> Index exists, skipping everything"
else
  exit 0
fi

# ensure, directory exists
mkdir -p "$DOWNLOAD_TARGET"

download_if_missing() {

  if [ -d "$DOWNLOAD_TARGET" ] && [ "$(ls -A "$DOWNLOAD_TARGET")" ]; then
    echo ">>> Baseline exists, skipping download"
  else
    echo ">>> Downloading PubMed data"
     while true; do
      uv run -m pybool_ir.cli pubmed download -b "$DOWNLOAD_TARGET" && break
      echo "Download failed – retrying in 30 seconds..."
      sleep 10
    done
  fi
}

if [ "$RUN_MODE" = "test" ]; then
  # Download raw PubMed data.
  echo ">>> TEST_MODE active: loading minimal dataset"
  download_if_missing --limit 1
  # uv run -m pybool_ir.cli pubmed download -b "$DOWNLOAD_TARGET" --limit 1

  # Convert the data into a single JSONL file.
  echo ">>> Prepare raw data"
  uv run -m pybool_ir.cli pubmed process -b "$DOWNLOAD_TARGET" -o full_tmp.jsonl

  # just for testing: use only one .xml.gz file
  [ ! -s full_tmp.jsonl ] && gzip -dc "$DOWNLOAD_TARGET"/*.xml.gz > full_tmp.jsonl 

  #head -n 1 full_tmp.jsonl > pubmed-processed.jsonl
  cat full_tmp.jsonl > pubmed-processed.jsonl
  rm full_tmp.jsonl
elif [ -f pubmed-processed.jsonl ]; then
  break
else
  echo "FULL MODE active: downloading full datase from baseline..."
  # Download raw PubMed data.
  download_if_missing
  
  # Convert the data into a single JSONL file.
  uv run -m pybool_ir.cli pubmed process -b "$DOWNLOAD_TARGET" -o pubmed-processed.jsonl
fi

# Index the processed PubMed data.
echo ">>> Creating Index..."
uv run -m pybool_ir.cli pubmed index -b pubmed-processed.jsonl -s 1 -i index
echo "DONE!"
