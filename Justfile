set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# extract 10, extract 5, extract 1
# This will extract grid-based zip files from region zip files.
extract res:
  find src/{{res}}z -name '*.zip' -print0 | xargs -0 -n 1 unzip -n -d src/{{res}}

# convert 10, convert 5, convert 1
# This will convert the grid-based zip files into GeoTIFF files.
# See github.com/unopengis/gmldem2tif for the tool.
convert res: 
  docker run --rm -u $(id -u):$(id -g) \
  -v $(realpath src/{{res}}):/src -v $(realpath dst/{{res}}):/dst \
  --entrypoint /bin/bash gmldem2tif \
  -c "bundle exec ruby gmldem2tif.rb -v -n $(nproc) -c zstd-max /src /dst"
