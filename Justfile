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

# Parameter for Source Cooperative
# - You need to additionally set environment variables from Source Cooperative.
bucket := "s3://us-west-2.opendata.source.coop/smartmaps/japan-geotiff-dem"
endpoint := "https://us-west-2.opendata.source.coop"

# upload documents to Source Cooperative
docs:
  aws s3 cp README.md {{bucket}}/README.md 
  aws s3 rm {{bucket}}/INCOMPLETE
#  aws s3 cp INCOMPLETE {{bucket}}/INCOMPLETE

# upload Japan GeoTIFF DEM data to Source Cooperative
sync res:
  aws s3 sync dst/{{res}} {{bucket}}/{{res}} --delete

# create quadrans version of GeoTIFF
quadrans res:
  ruby scripts/quadrans_script.rb {{res}}

