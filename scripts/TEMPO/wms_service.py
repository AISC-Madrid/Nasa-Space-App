import requests
import xml.etree.ElementTree as ET

class WMSService:
    def __init__(self, url):
        self.url = url
        self.layers = []

    def get_capabilities(self):
       
        response = requests.get(self.url)
        if response.status_code != 200:
            raise Exception(f"Error fetching WMS: {response.status_code}")
        
        tree = ET.fromstring(response.content)
        ns = {'wms': 'http://www.opengis.net/wms'}
        self.layers = [layer.text for layer in tree.findall('.//wms:Layer/wms:Name', ns)]
        return self.layers