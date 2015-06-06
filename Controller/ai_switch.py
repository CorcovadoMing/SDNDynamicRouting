from ryu.base import app_manager
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from ryu.topology.api import get_switch, get_link
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
from networkx.readwrite import json_graph
import networkx as nx
import array, requests, json, time

class AISwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(AISwitch, self).__init__(*args, **kwargs)

        self.datapaths = {}
        self.portmap = {}
        self.data = {}
        self.graph = nx.Graph()
        self.default_weight = 1

        self.active_flows = {}
        self.statistics = {}
        self.flow_rate = {}

        self._measurement = hub.spawn(self._measurement)
        self._update = hub.spawn(self._update)

        wsgi = kwargs['wsgi']
        wsgi.register(FlowViewer, {'ai_switch_app': self})

    def _update(self):
        while True:
            for i in self.data:
                src = int(i['src']['dpid'], 16)
                dst = int(i['dst']['dpid'], 16)
                self.portmap.setdefault(src, {})
                self.portmap.setdefault(dst, {})
                self.portmap[src][dst] = int(i['src']['port_no'])
                self.portmap[dst][src] = int(i['dst']['port_no'])
                self.graph.add_weighted_edges_from([(src, dst, self.default_weight)])

            if len(self.flow_rate) != 0 and len(self.active_flows) != 0:
                for key in self.flow_rate:
                    update_path = self.active_flows[key][:]
                    src, dst = int(key.split('-')[0]), int(key.split('-')[1])
                    if src < dst:
                        if update_path[-1] == src:
                            update_path.insert(0, dst)
                        else:
                            update_path.append(dst)
                    else:
                        if update_path[0] == src:
                            update_path.append(dst)
                        else:
                            update_path.insert(0, dst)
                    for i in xrange(len(update_path)-1):
                        s, t = update_path[i], update_path[i+1]
                        if s > t:
                            s, t = t, s
                        self.graph[s][t]['weight'] += self.flow_rate[key]
            hub.sleep(0.2)

    def _measurement(self):
        while True:
            print 'ActiveFlows: ', self.active_flows
            print 'FlowRate: ', self.flow_rate
            if len(self.active_flows) != 0:
                for path in self.active_flows:
                    if path.split('-')[0] == str(self.active_flows[path][-1]):
                        target = self.active_flows[path][0]
                    else:
                        target = self.active_flows[path][-1]
                    for dp in self.datapaths.values():
                        if dp.id == target:
                            self._request_stats(dp)
                            break
            hub.sleep(1)

    def _request_stats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        for flow in body:
            try:
                src, dst = int(flow.match['eth_src'].split(':')[-1], 16), int(flow.match['eth_dst'].split(':')[-1], 16)
                #print 'Datapath->' + str(ev.msg.datapath.id) + ' eth_src->' + str(flow.match['eth_src']) + ' eth_dst->' + str(flow.match['eth_dst']) + ' Byte Count->' + str(flow.byte_count)
                key = str(src) + '-' + str(dst)
                self.statistics.setdefault(key, [0, 0, 0]) # Now, Before, Timestamp
                if time.time() - self.statistics[key][2] > 0.5:
                    self.statistics[key][1] = self.statistics[key][0]
                    self.statistics[key][0] = flow.byte_count
                    self.statistics[key][2] = time.time()
                    self.flow_rate[key] = self.statistics[key][0] - self.statistics[key][1]
            except:
                try:
                    src, dst = int(flow.match['ipv4_dst'].split('.')[-1]), int(flow.match['ipv4_src'].split('.')[-1])
                    #print 'Datapath->' + str(ev.msg.datapath.id) + ' ipv4_src->' + str(flow.match['ipv4_src']) + ' ipv4_dst->' + str(flow.match['ipv4_dst']) + ' Byte Count->' + str(flow.byte_count)
                    key = str(src) + '-' + str(dst)
                    self.statistics.setdefault(key, [0, 0, 0]) # Now, Before, Timestamp
                    if time.time() - self.statistics[key][2] > 0.5:
                        self.statistics[key][1] = self.statistics[key][0]
                        self.statistics[key][0] = flow.byte_count
                        self.statistics[key][2] = time.time()
                        self.flow_rate[key] = self.statistics[key][0] - self.statistics[key][1]
                except:
                    pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def _switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_static_flow(datapath, 0, match, actions)

        actions = [parser.OFPActionOutput(1)]
        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst="10.0.0." + str(datapath.id))
        self._add_static_flow(datapath, 1, match, actions)
        match = parser.OFPMatch(eth_type=0x0806, arp_tpa="10.0.0." + str(datapath.id))
        self._add_static_flow(datapath, 1, match, actions)

    def _add_static_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
	                                    match=match, instructions=inst, command=ofproto.OFPFC_ADD)
        datapath.send_msg(mod)

    def _add_dynamic_flow(self, datapath, priority, out_port, dl_type, arp_tpa=None, arp_spa=None, nw_src=None, nw_dst=None, eth_src=None, eth_dst=None, soft_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(out_port)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if dl_type == 2048:
            match = parser.OFPMatch(eth_type=dl_type, ipv4_src=nw_src, ipv4_dst=nw_dst)
            src = int(nw_src.split('.')[-1])
            dst = int(nw_dst.split('.')[-1])
            key = str(src)+'-'+str(dst)
            self.active_flows.setdefault(key, [])
            self.active_flows[key].append(datapath.id)
            self.active_flows[key] = reduce(lambda a, b: b[0] in a and a or a + b, [[i] for i in self.active_flows[key]])
        elif dl_type == 2054:
            match = parser.OFPMatch(eth_type=dl_type, arp_spa=arp_tpa, arp_tpa=arp_tpa)
        elif dl_type == None:
            match = parser.OFPMatch(eth_src=eth_src, eth_dst=eth_dst)
            src = int(eth_src.split(':')[-1], 16)
            dst = int(eth_dst.split(':')[-1], 16)
            key = str(src)+'-'+str(dst)
            self.active_flows.setdefault(key, [])
            self.active_flows[key].append(datapath.id)
            self.active_flows[key] = reduce(lambda a, b: b[0] in a and a or a + b, [[i] for i in self.active_flows[key]])
        else:
            print 'ADD ERROR'

        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
	                                    match=match, instructions=inst,
	                                    command=ofproto.OFPFC_ADD, idle_timeout=soft_timeout,
	                                    hard_timeout=hard_timeout, flags=ofproto.OFPFF_SEND_FLOW_REM)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.logger.info('register datapath: %016d', datapath.id)
                self.datapaths[datapath.id] = datapath
                self.graph.add_node(datapath.id)
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.info('unregister datapath: %016d', datapath.id)
                del self.datapaths[datapath.id]
                self.graph.remove_node(datapath.id)

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def _flow_removed_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto

        if msg.reason == ofp.OFPRR_IDLE_TIMEOUT:
            reason = 'IDLE TIMEOUT'
        elif msg.reason == ofp.OFPRR_HARD_TIMEOUT:
            reason = 'HARD TIMEOUT'
        elif msg.reason == ofp.OFPRR_DELETE:
            reason = 'DELETE'
        elif msg.reason == ofp.OFPRR_GROUP_DELETE:
            reason = 'GROUP DELETE'
        else:
            reason = 'unknown'

        if 'ipv4_src' in msg.match:
            src = int(msg.match['ipv4_src'].split('.')[-1])
            dst = int(msg.match['ipv4_dst'].split('.')[-1])
            key = str(src)+'-'+str(dst)
            try:
                self.active_flows[key].remove(dp.id)
            except:
                pass
            try:
                if len(self.active_flows[key]) == 0:
                    del self.active_flows[key]
                    del self.statistics[key]
                    del self.flow_rate[key]
            except:
                pass

        elif 'eth_src' in msg.match:
            src = int(msg.match['eth_src'].split(':')[-1], 16)
            dst = int(msg.match['eth_dst'].split(':')[-1], 16)
            key = str(src)+'-'+str(dst)
            try:
                self.active_flows[key].remove(dp.id)
            except:
                pass
            try:
                if len(self.active_flows[key]) == 0:
                    del self.active_flows[key]
                    del self.statistics[key]
                    del self.flow_rate[key]
            except:
                pass

        elif 'arp_spa' in msg.match:
            pass

        else:
            print 'ERROR', msg.match



    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(array.array('B', msg.data))
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip4_pkt = pkt.get_protocol(ipv4.ipv4)

        if arp_pkt:
            links = get_link(self, None)
            self.data = [link.to_dict() for link in links]
            for i in self.data:
                src = int(i['src']['dpid'], 16)
                dst = int(i['dst']['dpid'], 16)
                self.portmap.setdefault(src, {})
                self.portmap.setdefault(dst, {})
                self.portmap[src][dst] = int(i['src']['port_no'])
                self.portmap[dst][src] = int(i['dst']['port_no'])
                try:
                    self.graph[src][dst]
                except:
                    self.graph.add_weighted_edges_from([(src, dst, self.default_weight)])

            src = int(arp_pkt.src_ip.split('.')[-1])
            dst = int(arp_pkt.dst_ip.split('.')[-1])

            path = nx.shortest_path(self.graph, source=ev.msg.datapath.id, target=dst)

            for i in xrange(len(path)-1):
                src = path[i]
                dst = path[i+1]

                # forward
                out_port = self.portmap[src][dst]
                self._add_dynamic_flow(self.datapaths[src], 1, out_port, 2048, nw_src=arp_pkt.src_ip, nw_dst=arp_pkt.dst_ip, soft_timeout=2)
                self._add_dynamic_flow(self.datapaths[src], 1, out_port, 2054, arp_spa=arp_pkt.src_ip, arp_tpa=arp_pkt.dst_ip, soft_timeout=2)

                # backward
                out_port = self.portmap[dst][src]
                self._add_dynamic_flow(self.datapaths[dst], 1, out_port, 2048, nw_src=arp_pkt.dst_ip, nw_dst=arp_pkt.src_ip, soft_timeout=2)
                self._add_dynamic_flow(self.datapaths[dst], 1, out_port, 2054, arp_spa=arp_pkt.dst_ip, arp_tpa=arp_pkt.src_ip, soft_timeout=2)

            src = path[0]
            dst = path[1]
            out_port = self.portmap[src][dst]
            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                data = msg.data
            out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
            datapath.send_msg(out)

        elif eth_pkt:
            if eth_pkt.dst.split(':')[1] == '00' and eth_pkt.src.split(':')[1] == '00':
                self.logger.info("packet in %s %s %s %s", datapath.id, eth_pkt.src, eth_pkt.dst, in_port)
                links = get_link(self, None)
                self.data = [link.to_dict() for link in links]
                for i in self.data:
                    src = int(i['src']['dpid'], 16)
                    dst = int(i['dst']['dpid'], 16)
                    self.portmap.setdefault(src, {})
                    self.portmap.setdefault(dst, {})
                    self.portmap[src][dst] = int(i['src']['port_no'])
                    self.portmap[dst][src] = int(i['dst']['port_no'])
                    try:
                        self.graph[src][dst]
                    except:
                        self.graph.add_weighted_edges_from([(src, dst, self.default_weight)])

                src = int(eth_pkt.src.split(':')[-1], 16)
                dst = int(eth_pkt.dst.split(':')[-1], 16)
                path = nx.dijkstra_path(self.graph, source=datapath.id, target=dst)

                for i in xrange(len(path)-1):
                    src = path[i]
                    dst = path[i+1]

                    # forward
                    out_port = self.portmap[src][dst]
                    self._add_dynamic_flow(self.datapaths[src], 1, out_port, None, eth_src=eth_pkt.src, eth_dst=eth_pkt.dst, soft_timeout=2)

                    # backward
                    out_port = self.portmap[dst][src]
                    self._add_dynamic_flow(self.datapaths[dst], 1, out_port, None, eth_src=eth_pkt.dst, eth_dst=eth_pkt.src, soft_timeout=2)

                src = path[0]
                dst = path[1]
                out_port = self.portmap[src][dst]
                actions = [parser.OFPActionOutput(out_port)]
                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data
                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                      in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)

        elif ip4_pkt:
            print 'IP4 NEED HANDLE'

        else:
            print 'ERROR'

class FlowViewer(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(FlowViewer, self).__init__(req, link, data, **config)
        self.ai_switch_app = data['ai_switch_app']

    @route('flows', '/stats/activeflows',
           methods=['GET'])
    def _list_flows(self, req, **kwargs):
        body = json.dumps(self.ai_switch_app.active_flows)
        return Response(content_type='application/json', body=body)

    @route('rate', '/stats/flowrate', methods=['GET'])
    def _list_flow_rate(self, req, **kwargs):
        body = json.dumps(self.ai_switch_app.flow_rate)
        return Response(content_type='application/json', body=body)

    @route('network', '/stats/network', methods=['GET'])
    def _list_net(self, req, **kwargs):
        body = json.dumps(json_graph.node_link_data(self.ai_switch_app.graph))
        return Response(content_type='application/json', body=body)
