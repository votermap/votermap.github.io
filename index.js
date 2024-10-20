document.addEventListener('DOMContentLoaded', function() {
    const mapConfig = {
        "map_type": "dot density",
        "dot_scale": 1,
        "group_by_column": "candidate",
        "symbology_column": "votes",
        "color_associations": {
            "Biden": "blue",
            "Trump": "red",
            "Clinton": "blue",
            "Other": "yellow"
        },
        "spatial_aggregation": "census block",
        "color_associations_hex": {
            "Biden": "#0000FF",
            "Clinton": "#0000FF",
            "Trump": "#FF0000",
            "Other": "#FFFF00"
        }
    };

    const beforeMap = new maplibregl.Map({
        container: 'before',
        style: 'https://tiles.stadiamaps.com/styles/alidade_smooth.json',
        center: [-98.5795, 39.8283],
        zoom: 3.5,
        maxZoom: 10
    });

    const afterMap = new maplibregl.Map({
        container: 'after',
        style: 'https://tiles.stadiamaps.com/styles/alidade_smooth.json',
        center: [-98.5795, 39.8283],
        zoom: 3.5,
        maxZoom: 10
    });

    const container = '#comparison-container';
    const compare = new maplibregl.Compare(beforeMap, afterMap, container, {
        mousemove: true,
        orientation: 'vertical'
    });

    beforeMap.on('load', () => {
        addDotDensityLayer(beforeMap, mapConfig.symbology_column, mapConfig.group_by_column, mapConfig.dot_scale, document.body, mapConfig, '2016');
    });

    afterMap.on('load', () => {
        addDotDensityLayer(afterMap, mapConfig.symbology_column, mapConfig.group_by_column, mapConfig.dot_scale, document.body, mapConfig, '2020');
    });
});

function addDotDensityLayer(map, symbologyColumn, groupByColumn, dotScale, element, mapConfig, year) {
    const categories = Object.keys(mapConfig.color_associations_hex);
    
    const colorScale = d => {
        return mapConfig.color_associations_hex[d] || mapConfig.color_associations_hex[''];
    };

    map.addSource('dot-density-source', {
        type: 'vector',
        tiles: [`https://resultmap.s3.us-east-2.amazonaws.com/tiles/{z}/{x}/{y}.pbf`],
        // tiles: [`http://localhost:7800/services/all/tiles/{z}/{x}/{y}.pbf`],
        // tiles: [`http://localhost:1234/tiles/static/{z}/{x}/{y}.pbf`],
        minzoom: 0,
        maxzoom: 10
    });

    map.addLayer({
        id: 'dot-density-layer',
        type: 'circle',
        source: 'dot-density-source',
        'source-layer': `election_results_${year}`,
        paint: {
            'circle-radius': [
                'interpolate',
                ['exponential', 2],
                ['zoom'],
                0, 1,
                8, 1,
                10, 1,
                22, 256
            ],
            'circle-color': [
                'match',
                ['get', 'category'],
                ...categories.flatMap(category => [category, colorScale(category)]),
                colorScale(categories[0])
            ],
            'circle-opacity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 0.06,
                9, 0.06,
                13, 0.4
              ]
        }
    });

    addDotDensityLegend(element, categories, colorScale, groupByColumn || symbologyColumn, dotScale, mapConfig, year);
}

function addDotDensityLegend(element, categories, colorScale, groupByColumn, dotScale, mapConfig, year) {
    const legend = createLegendContainer(element, year);

    const title = document.createElement('h4');
    title.style.margin = '0 0 10px 0';
    title.style.padding = '0';
    title.textContent = `${year}`;
    legend.appendChild(title);

    categories.forEach(category => {
        if ((year === '2016' && category !== 'Biden') || (year === '2020' && category !== 'Clinton')) {
            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.marginBottom = '5px';

            const color = document.createElement('div');
            color.style.width = '20px';
            color.style.height = '20px';
            color.style.backgroundColor = colorScale(category);
            color.style.marginRight = '5px';

            const label = document.createElement('span');
            label.textContent = category;

            item.appendChild(color);
            item.appendChild(label);
            legend.appendChild(item);
        }
    });
}

function createLegendContainer(element, year) {
    let legend = element.querySelector(`.map-legend-${year}`);
    if (!legend) {
        legend = document.createElement('div');
        legend.className = `map-legend map-legend-${year}`;
        legend.style.left = year === '2016' ? '20px' : 'auto';
        legend.style.right = year === '2020' ? '20px' : 'auto';
        element.appendChild(legend);
    } else {
        legend.innerHTML = '';
    }
    return legend;
}