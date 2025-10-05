import folium

class WMSLayer:
    def __init__(self, name, layer_name, url, time=None):
        self.name = name
        self.layer_name = layer_name
        self.url = url
        self.time = time

    def add_to_map(self, folium_map):
        folium.WmsTileLayer(
            url=self.url,
            name=self.name,
            layers=self.layer_name,
            fmt="image/png",
            transparent=True,
            overlay=True,
            control=True,
            time=self.time
        ).add_to(folium_map)
