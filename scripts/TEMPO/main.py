from wms_layer import WMSLayer
from wms_map import WMSMap
from wms_service import WMSService
from utils import format_date

# Date
year, month, day = 2025, 9, 1
formatted_date = format_date(year, month, day)

#Location
location = [40, 3.7]
zoom_start = 10

# URL WMS
wms_url = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities"

# Map
wms_map = WMSMap(location=location, zoom_start=zoom_start, tiles="Esri.WorldImagery")

# Layers

# Nitrogen Dioxide
l_1 = WMSLayer("Nitrogen Dioxide Levels", "OMI_Nitrogen_Dioxide_Tropo_Column", wms_url, time=formatted_date)
#Formaldehyde
l_2 = WMSLayer("Formaldehyde Levels", "TEMPO_L3_Formaldehyde_Vertical_Column", wms_url, time=formatted_date)
#Aerosol Index (AI)
l_3 = WMSLayer("Aerosol Index (AI)", "TEMPO_L3_Ozone_UV_Aerosol_Index", wms_url, time=formatted_date)
#Particulate Matter (PM)
l_4 = WMSLayer("Particulate Matter (PM)", "MODIS_Aqua_Aerosol_Optical_Depth_3km", wms_url, time=formatted_date)
#Ozone
l_5 = WMSLayer("Ozone Levels", "TEMPO_L3_Ozone_Column_Amount", wms_url, time=formatted_date)

layers = [l_1, l_2, l_3, l_4, l_5]

# Add layers
for layers in layers:
    wms_map.add_layer(layers)

# Layer control
wms_map.add_layer_control()

wms_map.add_pin()

# Save map
wms_map.save("scripts/TEMPO/maps/final_map.html")