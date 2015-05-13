$("#icon").click(function () {
    $("#sidebar").toggleClass("hide");
    $("#main").toggleClass("hwidth");
});

function httpGet(theUrl) {
    var xmlHttp = null;
    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false );
    xmlHttp.send();
    return xmlHttp.responseText;
}

function graph_build() {
    var nodes = JSON.parse(httpGet("http://192.168.59.103:8080/stats/switches"));
    var edges_data = JSON.parse(httpGet("http://192.168.59.103:8080/v1.0/topology/links"));
    var edges_connection = []
    for (var i = 0; i < edges_data.length; ++i) {
        var src = parseInt(edges_data[i]['src']['dpid'], 16);
        var dst = parseInt(edges_data[i]['dst']['dpid'], 16);
        edges_connection.push([src, dst, 1]);
    };
    G.add_nodes_from(nodes);
    G.add_weighted_edges_from(edges_connection);
    graph_update(nodes);
}

var count
function graph_update(prenodes) {
    if (count) {
        for (var i = 0; i < count; i += 1) {
            var countid = i + 1;
            $("#"+countid).remove();
        }
    }

    var nodes = JSON.parse(httpGet("http://192.168.59.103:8080/stats/switches"));
    var d = prenodes.diff(nodes);
    var n = nodes.diff(prenodes);
    if (d.length !== 0) {
        G.remove_nodes_from(d);
    }
    if (n.length !== 0) {
        G.add_nodes_from(n);
    }

    var net = JSON.parse(httpGet("http://192.168.59.103:8080/stats/network"))["links"];
    var edges_connection = []
    for (var i = 0; i < net.length; ++i) {
        edges_connection.push([net[i]["source"]+1, net[i]["target"]+1, net[i]["weight"]]);
        console.log(net[i]["source"]+1)
        console.log(net[i]["target"]+1)
        console.log(net[i]["weight"])
    }

    var activeflows = JSON.parse(httpGet("http://192.168.59.103:8080/stats/activeflows"));
    var flowrate = JSON.parse(httpGet("http://192.168.59.103:8080/stats/flowrate"));
    count = 0;
    for (var item in activeflows) { 
        count += 1;
        $("#list").append('<h2 id="' + count + '">' + item + '<br>' + activeflows[item] + ': ' + flowrate[item] + ' Bps </h2>'); 
    };
    document.getElementById('flow-count').innerHTML = count;

    G.add_weighted_edges_from(edges_connection);
    setTimeout(graph_update.bind(null, nodes), 1000);
}

Array.prototype.diff = function(a) {
    return this.filter(function(i) {return a.indexOf(i) < 0;});
};

G = jsnx.Graph(); 
graph_build();

jsnx.draw(G, {
    'element': '#canvas',
    'with_labels': true,
    'with_edge_labels': false,
    'weighted': true,
    'weighted_stroke': true,
    'node_style': {
        'stroke': '#FFF',
        'fill': '#ABC',
        'cursor': 'pointer'
    },
    'node_attr': {
      'r': 15
    },
    'label_style': {
        'text-anchor': 'middle',
        'dominant-baseline': 'central',
        'cursor': 'pointer',
        '-webkit-user-select': 'none',
        'fill': '#000'
    },
    'edge_label_style': {
        'font-size': '0.7em',
        'text-anchor': 'middle',
        '-webkit-user-select': 'none'
    },
    'edge_style': {
        'fill': function(d) {
            var color;
            if (d.data.weighted > 200) {
                color = '#591';
            }
            else {
                color = '#951';
            }
            return color;
        },
        'stroke-width': 10
    },
    'layout_attr': {
        'charge': -1500,
        'linkDistance': 70
    }, 
    'pan_zoom': {
        'enabled': false, 
        'scale': false
    }
}, true);
