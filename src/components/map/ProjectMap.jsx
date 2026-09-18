import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import 'mapbox-gl/dist/mapbox-gl.css'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'

const TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

function featureCollection(sites) { return { type: 'FeatureCollection', features: sites.map((site) => ({ id: site.id, type: 'Feature', geometry: site.geometry, properties: { site_id: site.id, name: site.name } })) } }

export default function ProjectMap({ sites, selectedSiteId, onSelectSite, drawing, onDrawComplete }) {
  const containerRef = useRef(null); const mapRef = useRef(null); const drawRef = useRef(null); const onSelectRef = useRef(onSelectSite); const onDrawRef = useRef(onDrawComplete)
  useEffect(() => { onSelectRef.current = onSelectSite; onDrawRef.current = onDrawComplete }, [onSelectSite, onDrawComplete])
  useEffect(() => {
    if (!TOKEN || !containerRef.current) return
    mapboxgl.accessToken = TOKEN
    const map = new mapboxgl.Map({ container: containerRef.current, style: 'mapbox://styles/mapbox/light-v11', center: [78.5, 21], zoom: 4.2, attributionControl: false })
    const draw = new MapboxDraw({ displayControlsDefault: false, controls: { polygon: false, trash: false }, styles: [{ id: 'gl-draw-polygon-fill', type: 'fill', filter: ['all', ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']], paint: { 'fill-color': '#e39b54', 'fill-opacity': 0.22 } }] })
    map.addControl(new mapboxgl.NavigationControl(), 'top-right'); map.addControl(draw, 'top-left'); mapRef.current = map; drawRef.current = draw
    map.on('load', () => { map.addSource('sites', { type: 'geojson', data: featureCollection(sites) }); map.addLayer({ id: 'site-fill', type: 'fill', source: 'sites', paint: { 'fill-color': ['case', ['boolean', ['feature-state', 'selected'], false], '#e39b54', '#1e7770'], 'fill-opacity': 0.26 } }); map.addLayer({ id: 'site-outline', type: 'line', source: 'sites', paint: { 'line-color': ['case', ['boolean', ['feature-state', 'selected'], false], '#b56a27', '#1e7770'], 'line-width': 2 } }); map.on('click', 'site-fill', (event) => { const siteId = event.features?.[0]?.properties?.site_id; if (siteId) onSelectRef.current(Number(siteId)) }); map.on('mouseenter', 'site-fill', () => { map.getCanvas().style.cursor = 'pointer' }); map.on('mouseleave', 'site-fill', () => { map.getCanvas().style.cursor = '' }); fitMap(map, sites) }); map.on('draw.create', (event) => { const feature = event.features?.[0]; if (feature?.geometry?.type === 'Polygon') onDrawRef.current(feature.geometry); draw.deleteAll() })
    return () => { map.remove(); mapRef.current = null; drawRef.current = null }
  }, [])
  useEffect(() => { const map = mapRef.current; if (!map?.isStyleLoaded() || !map.getSource('sites')) return; map.getSource('sites').setData(featureCollection(sites)); sites.forEach((site) => { map.setFeatureState({ source: 'sites', id: site.id }, { selected: site.id === selectedSiteId }) }); fitMap(map, sites) }, [sites, selectedSiteId])
  useEffect(() => { if (drawing && drawRef.current) drawRef.current.changeMode('draw_polygon'); else if (!drawing && drawRef.current?.getMode() === 'draw_polygon') drawRef.current.changeMode('simple_select') }, [drawing])
  if (!TOKEN) return <div className="map-missing"><div className="map-missing-grid" /><div><strong>Mapbox token required</strong><p>Add <code>VITE_MAPBOX_TOKEN</code> to your frontend environment to enable the interactive map.</p></div></div>
  return <div className="map-wrapper"><div ref={containerRef} className="map-container" />{sites.length === 0 && <div className="map-empty">Draw your first polygon to add a site.</div>}</div>
}

function fitMap(map, sites) { if (!sites.length) return; const bounds = new mapboxgl.LngLatBounds(); sites.forEach((site) => site.geometry.coordinates[0].forEach(([lng, lat]) => bounds.extend([lng, lat]))); if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 70, maxZoom: 11, duration: 500 }) }
