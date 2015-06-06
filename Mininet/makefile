all:
	@echo "Use make [local|remote]"

local:
	@mn --custom topo.py --topo project --switch ovsk,protocols=OpenFlow13 --controller ref --mac

remote:
	@sudo mn --link tc,bw=1 --custom topo.py --topo project --switch ovsk,protocols=OpenFlow13 --controller remote,ip=192.168.59.103 --mac

remote2:
	@sudo mn --link tc,bw=1 --custom topo2.py --topo project --switch ovsk,protocols=OpenFlow13 --controller remote,ip=192.168.59.103 --mac

remote3:
	@mn --link tc,bw=0.1 --custom topo3.py --topo project --switch user --controller remote,ip=192.168.59.103 --mac
