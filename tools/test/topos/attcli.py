#!/usr/bin/python

"""
CLI for test with AttMplsTopo
"""

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.util import quietRun
from mininet.log import setLogLevel, info, output, error
from mininet.util import waitListening
from mininet.node import RemoteController

from attmplsfast import AttMplsTopo

from subprocess import PIPE, STDOUT
import random

class IperfCLI( CLI ):
    "CLI with iperf UDP traffic generation"

    def __init__( self, net, *args, **kwargs ):
        self.iperfs = {}
        self.bw = '12k'
        self.mn = net
        self.start()
        quietRun( 'rm /tmp/*.iperf' )
        CLI.__init__( self, net, *args, **kwargs )

    def __del__( self ):
        "Destructor: kill *all* iperf servers and clients!"
        quietRun( 'pkill -9 iperf' )

    def start( self ):
        "Start iperf servers"
        for h in self.mn.hosts:
            with open( '/tmp/%s.iperf' % h, 'w' ) as f:
                cmd = 'iperf -f k -i 1 -s -u'
                popen = h.popen( cmd, stdin=PIPE, stdout=f, stderr=STDOUT )
                self.iperfs[ h ] = popen

    def udpstart( self, h1, h2, bw):
        "Start up a udp iperf from h1 to h2 with bw bw"
        # For udp we don't have to wait for startup
        self.udpstop( h1 )
        h1.cmdPrint( 'iperf -c', h2.IP(),
                     '-t 36000 -u -b', bw,
                     '1>/tmp/%s.client 2>&1 &' % h1 )

    def udpstop( self, h ):
        "Stop udp client on host h"
        h.cmdPrint( 'kill %iperf && wait' )

    def do_udp( self, line ):
        """udp h1 h2 [rate]: start a udp iperf session from h1 to h2
           rate: udp transmit rate [12k]"""
        args = line.split()
        if len( args ) not in ( 2, 3 ):
            error( 'usage: udp h1 h2 [rate]\n' )
            return
        h1, h2 = self.mn.get( *args[ :2 ] )
        bw = self.bw if len( args ) == 2 else args[ 2 ]
        self.udpstart( h1, h2, bw )

    def do_stop( self, line ):
        "Stop iperf client/server on host"
        if not line:
            error( 'usage: stop [hostname|all]' )
        if line == 'all':
            hosts = self.mn.hosts
        else:
            hosts = [ self.get( line ) ]
        for h in hosts:
            self.udpstop( h )

    def do_bw( self, line ):
        "Report iperf bandwidth"
        output( "Last reported iperf UDP server input bandwidth:\n" )
        for h in self.mn.hosts:
            out = h.cmd( 'tail -1 /tmp/%s.iperf' % h )
            output( '%s:' % h, out )

    def do_rand( self, line ):
        """Start up a random set of N flows (default: 10)
           at the given bandwidth (default: 12k)
           Note: this may replace existing flows"""
        output( 'Starting/restarting random flows...\n' )
        args = line.split()
        N = 10 if not args else int( args[ 0 ] )
        bw = self.bw if len( args ) < 2 else args[ 1 ]
        hosts = random.sample( self.mn.hosts, N )
        for h1 in hosts:
            dests = list( self.mn.hosts )
            dests.remove( h1 )
            h2 = random.choice( dests )
            self.udpstart( h1, h2, bw )

    def do_jobs( self, line ):
        "Print iperf jobs"
        output( "Currently running jobs:\n" )
        for h in self.mn.hosts:
            output( '%s:' % h, h.cmd( 'jobs' ).strip(), '\n' )


def run( Topo=AttMplsTopo ):
    "Create network and run CLI"
    topo = Topo()
    net = Mininet( topo=topo, controller=RemoteController )
    net.start()
    info( '\n### Welcome to the custom iperf udp CLI!\n'
          '###\n'
          '### udp h1 h2 [bw]   start iperf udp from h1 to h2\n'
          '### stop h1 h2       stop iperf udp from h1 to h2\n'
          '### rand [N]         start/restart N random udp iperfs\n'
          '### bw               show last reported udp input bandwidth\n'
          '### jobs             list current jobs\n\n' )
    IperfCLI( net )
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    run()
