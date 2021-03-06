import Pyro4
import kid_readout.utils.mini_aggregator
import kid_readout.utils.catcher
import cProfile

ns = Pyro4.naming.locateNS()

try:
    uri = ns.lookup("minicoord")
    proxy = Pyro4.Proxy(uri)
    proxy.quit()
    ns.remove("minicoord")
    print "removed old minicoord"
except:
    pass

class MiniCoordinator():
    def __init__(self):
        
        self.miniagg = kid_readout.utils.mini_aggregator.MiniAggregator()
        self.catcher = kid_readout.utils.catcher.DemultiplexCatcher(self.miniagg.create_data_products_debug)
        
        self.catcher.start_data_thread()
        
    def set_channel_ids(self, ids):
        return self.catcher.set_channel_ids(ids)
        
    def get_data(self, data_request):
        return self.miniagg.get_data(data_request)


minicoord = MiniCoordinator()
daemon = Pyro4.Daemon()
uri = daemon.register(minicoord)
ns.register("minicoord", uri)

daemon.requestLoop()


