# Japan GeoTIFF DEM Utility for Mapterhorn

## Overview

This repository holds the pipeline used to convert the Japan
Geospatial Information Authority's (GSI, 国土地理院) 基盤地図情報
Digital Elevation Model (DEM) data — available at 10m, 5m, and 1m
resolutions — from its native zipped GML distribution into GeoTIFF,
and publish it to Source Cooperative. See `CLAUDE.md` for the pipeline
stages (`just extract` / `skip-published` / `convert` / `quadrans` /
`sync` / `filelists` / `docs`) and operational notes, and
`DECISIONS.md` for the reasoning behind them.

For the dataset itself — what's actually published, format, license,
attribution — see `source-coop/README.md`, which is what's uploaded to
the product root on Source Cooperative rather than this file.

## Contents

- `10/` - 10m resolution DEM
- `5/` - 5m resolution DEM
- `1/` - 1m resolution DEM

Each resolution folder contains one GeoTIFF per source mesh (EPSG:6668).

## License

See below: approval and copyright.

## Clarifications

測量法に基づく国土地理院長承認（複製）R8JHf51

不特定多数の者が提供を受けることができる状態に置く措置をとるために本製品を複製する場合には、国土地理院の長の承認を得なければなりません。

Approval for Reproduction pursuant to the Survey Act, granted by the Director-General of the Geospatial Information Authority of Japan (R8JHf51).

When reproducing this product in order to make it available to the general public, approval from the Director-General of the Geospatial Information Authority of Japan must be obtained.

## Links

- Source Cooperative "smartmaps/japan-geotiff-dem"
  https://source.coop/smartmaps/japan-geotiff-dem
