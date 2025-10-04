import folium

class WMSMap:
    def __init__(self, location, zoom_start, tiles="OpenStreetMap"):
        self.map = folium.Map(location=location, zoom_start=zoom_start, tiles=tiles)
        self.layers = []
        self.location = location
        self.zoom_start = zoom_start

    def add_layer(self, wms_layer):
        wms_layer.add_to_map(self.map)
        self.layers.append(wms_layer)

    def add_layer_control(self):
        folium.LayerControl().add_to(self.map)

    def add_pin(self):
        folium.Marker(
    location=self.location,
    icon=folium.Icon(color="red", icon="person", prefix="fa"),
    ).add_to(self.map)

    def show(self):
        return self.map

    def save(self, filename="map.html"):
        self.map.save(filename)
        print(f"Map saved to {filename}")
