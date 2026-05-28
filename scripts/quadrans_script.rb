#!/usr/bin/env ruby

require 'fileutils'
require 'open3'

class Quadrans
  NORTH = :NORTH
  EAST  = :EAST
  SOUTH = :SOUTH
  WEST  = :WEST

  def self.of(code)
    code = code.to_i
    y = code / 100    # 緯度番号
    x = code % 100    # 経度番号

    y >= 62 ? NORTH :
    x >= 38 ? EAST  :
    x <= 32 ? SOUTH : WEST
  end

  def initialize
    @store = Hash.new { |h, k| h[k] = [] }
  end

  def add(mesh_code, path)
    area = self.class.of(mesh_code)
    @store[area] << path
  end

  def each(&block)
    @store.each(&block)
  end
end

unless ARGV.size == 1
  puts "使い方: ruby quadrans_script.rb <res>"
  exit(1)
end
res = ARGV[0]
SRC_DIR = "dst/#{res}"
OUT_DIR = "quadrans/#{res}"
BLOCK_SIZE = 512

FileUtils.mkdir_p(OUT_DIR)

quads = Quadrans.new

Dir.glob("#{SRC_DIR}/*.tif").each do |tif_path|
  mesh_code_str = File.basename(tif_path).split('-')[2] rescue nil
  next unless mesh_code_str && mesh_code_str =~ /^\d+$/
  quads.add(mesh_code_str, tif_path)
end

quads.each do |region, paths|
  next if paths.empty?
  region_name = region.to_s.downcase
  vrt_path  = "#{OUT_DIR}/#{region_name}.vrt"
  final_tif = "#{OUT_DIR}/#{region_name}.tif"
  list_file = "#{OUT_DIR}/inputs_#{region_name}.txt"

  File.open(list_file, 'w') { |fh| paths.each { |path| fh.puts(path) } }

  # 仮想結合 (VRT生成)
  vrt_cmd = [
    "gdalbuildvrt", "-input_file_list", list_file, vrt_path
  ]
  puts "Running: #{vrt_cmd.join(' ')}"
  _, stderr, status = Open3.capture3(*vrt_cmd)
  raise "gdalbuildvrt failed: #{stderr}" unless status.success?

  # Mapterhorn互換 LERC化


  out_cmd = [
    "docker", "run", "--rm",
    "-v", "#{Dir.pwd}:/data",
    "-w", "/data",
    "ghcr.io/osgeo/gdal:alpine-small-latest",
    "gdal_translate", vrt_path, final_tif,
    "-co", "COMPRESS=LERC",
    "-co", "MAX_Z_ERROR=0.01",
    "-co", "COPY_SRC_OVERVIEWS=NO",
    "-co", "TILED=YES",
    "-co", "BLOCKXSIZE=#{BLOCK_SIZE}",
    "-co", "BLOCKYSIZE=#{BLOCK_SIZE}",
    "-co", "BIGTIFF=YES"
  ]
  puts "Running: #{out_cmd.join(' ')}"
  _, stderr, status = Open3.capture3(*out_cmd)
  raise "gdal_translate failed: #{stderr}" unless status.success?

  puts "[#{region}] 完了: #{final_tif}"
end

puts "全領域の処理が正常に終わりました"
