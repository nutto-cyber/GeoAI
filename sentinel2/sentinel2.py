"""
Sentinel-2 cloud-free median composite over Thailand (2026), visualized with geemap.
Ported from sentinel2_template.html (Google Maps JS + Earth Engine tile layers).
"""

import ee
import geemap

GEE_PROJECT_ID = "peak-plasma-485606-u1"

START_DATE = "2026-01-01"
END_DATE = "2026-12-31"
CLOUD_FILTER = 60          # max scene-level cloudy pixel percentage to include
CLD_PRB_THRESH = 40        # s2cloudless cloud probability threshold (%)

VIS_PARAMS = {
    "bands": ["B4", "B3", "B2"],
    "min": 0,
    "max": 3000,
    "gamma": 1.1,
}


def get_thailand_boundary():
    countries = ee.FeatureCollection("FAO/GAUL/2015/level0")
    return countries.filter(ee.Filter.eq("ADM0_NAME", "Thailand"))


def get_s2_sr_cld_col(aoi, start_date, end_date):
    s2_sr_col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", CLOUD_FILTER))
    )
    s2_cloudless_col = (
        ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )
    return ee.ImageCollection(
        ee.Join.saveFirst("s2cloudless").apply(
            primary=s2_sr_col,
            secondary=s2_cloudless_col,
            condition=ee.Filter.equals(
                leftField="system:index", rightField="system:index"
            ),
        )
    )


def add_cloud_mask(img):
    cld_prb = ee.Image(img.get("s2cloudless")).select("probability")
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename("clouds")
    return img.addBands(is_cloud)


def apply_cloud_mask(img):
    not_cld = img.select("clouds").Not()
    return img.select("B.*").updateMask(not_cld)


def build_s2_composite(aoi):
    s2_sr_cld_col = get_s2_sr_cld_col(aoi, START_DATE, END_DATE)
    s2_masked = (
        s2_sr_cld_col.map(add_cloud_mask)
        .map(apply_cloud_mask)
    )
    return s2_masked.median().clip(aoi)


def main():
    ee.Initialize(project=GEE_PROJECT_ID)

    aoi = get_thailand_boundary()
    composite = build_s2_composite(aoi)
    boundary_outline = ee.Image().byte().paint(
        featureCollection=aoi, color=1, width=2
    )

    Map = geemap.Map(center=[13.0, 101.0], zoom=6, add_google_map=False)
    Map.add_basemap("SATELLITE")

    Map.addLayer(
        composite,
        VIS_PARAMS,
        "Sentinel-2 median composite",
    )
    Map.addLayer(
        boundary_outline,
        {"palette": ["ffff00"]},
        "Thailand boundary",
    )
    Map.centerObject(aoi, 6)
    Map.add_layer_control()

    legend_text = (
        "Cloud-free median composite, true color (B4/B3/B2), "
        f"{START_DATE} to {END_DATE}.<br>"
        "Source: Sentinel-2 SR Harmonized + s2cloudless, Google Earth Engine."
    )
    Map.add_html(
        html=(
            '<div style="font-size:13px; max-width:260px;">'
            f"<b>Sentinel-2 &mdash; Thailand 2026</b><br>{legend_text}"
            "</div>"
        ),
        position="topleft",
    )

    Map.to_html("Sentinel2.html")
    print("Saved map to Sentinel2.html")


if __name__ == "__main__":
    main()
