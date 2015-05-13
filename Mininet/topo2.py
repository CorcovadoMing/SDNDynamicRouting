"""Custom topology example

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=project' from the command line.
"""

from mininet.topo import Topo

class ProjectTopo(Topo):

    def __init__(self):

        super(ProjectTopo, self).__init__()

        topo_size = 3

	link_from = [0,1,2]
	link_to = [1,2,0]

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
