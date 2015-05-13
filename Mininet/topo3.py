from mininet.net import Mininet
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.node import UserSwitch,RemoteController
from mininet.term import makeTerm
import os, time

class MyTopo( Topo ):
  "Simple topology example."

  def __init__( self):
      "Create custom topo."

      # Add default members to class.
      Topo.__init__(self)

      # Add nodes
        
      Host1=self.addHost('h1', ip='10.0.0.1/24')
      Host2=self.addHost('h2', ip='10.0.0.2/24')
      Host3=self.addHost('h3', ip='10.0.0.3/24')
      Host4=self.addHost('h4', ip='10.0.0.4/24')
      Host5=self.addHost('h5', ip='10.0.0.5/24')
      Host6=self.addHost('h6', ip='10.0.0.6/24')
      Host7=self.addHost('h7', ip='10.0.0.7/24')
      Host8=self.addHost('h8', ip='10.0.0.8/24')
      switch1=self.addSwitch('s1')
      switch2=self.addSwitch('s2')
      switch3=self.addSwitch('s3')
      switch4=self.addSwitch('s4')
      switch5=self.addSwitch('s5')
      switch6=self.addSwitch('s6')
      switch7=self.addSwitch('s7')
      switch8=self.addSwitch('s8')
      # Add edges
      self.addLink( Host1, switch1, 1, 1)
      self.addLink( Host2, switch2, 1, 1)
      self.addLink( Host3, switch3, 1, 1)
      self.addLink( Host4, switch4, 1, 1)
      self.addLink( Host5, switch5, 1, 1)
      self.addLink( Host6, switch6, 1, 1)
      self.addLink( Host7, switch7, 1, 1)
      self.addLink( Host8, switch8, 1, 1)
      self.addLink( switch1, switch2)
      self.addLink( switch1, switch3)
      self.addLink( switch1, switch4)
      self.addLink( switch4, switch7)
      self.addLink( switch7, switch8)
      self.addLink( switch2, switch5)
      self.addLink( switch5, switch8)
      self.addLink( switch3, switch6)
      self.addLink( switch6, switch8)
######Starting mininet
topos = { 'project': ( lambda: MyTopo() ) }
