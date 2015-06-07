"""Custom topology example

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=project' from the command line.
"""

from mininet.topo import Topo

class ProjectTopo(Topo):

    def __init__(self):

        super(ProjectTopo, self).__init__()

        topo_size = 20

	link_from = [0,0,0,0,1,1,1,2,2,2,2,3,3,3,4,5,5,6,6,6,6,7,7,7,7,8,8,8,9,9,9,9,10,11,11,12,12,12,13,13,13,14,14,14,15,16,17,18]
	link_to = [1,2,3,4,2,5,6,3,6,7,8,4,8,10,10,6,11,7,8,11,12,8,11,12,13,9,13,14,10,14,15,18,15,12,16,13,16,17,14,17,19,15,18,19,17,17,19,19]

        #hosts = [self.addHost('h%s' % h) for h in xrange(1, topo_size + 1)]
        #switches = [self.addSwitch('s%s' % s) for s in xrange(1, topo_size + 1)]

        for n in xrange(1, topo_size+1):
            self.addSwitch('s%d' % int(n))
            self.addHost('h%d' % int(n))
            self.addLink('h%d' % int(n), 's%d' % int(n))
        #for host, switch in zip(hosts, switches):
        #    self.addLink(host, switch)

	for lf, lt in zip(link_from, link_to):
            #self.addLink(switches[lf], switches[lt])
            print int(lf+1), int(lt+1)
            self.addLink('s%d' % int(lf+1), 's%d' % int(lt+1))

topos = { 'project': ( lambda: ProjectTopo() ) }
