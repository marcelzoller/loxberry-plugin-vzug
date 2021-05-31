#!/usr/bin/perl

# Einbinden von Module
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use IO::Socket::INET;
use LWP::Simple;
use Net::Ping;
use IO::Socket;
use strict;


print "Content-type: text/html\n\n";

# Konfig auslesen
my %pcfg;
my %miniservers;
tie %pcfg, "Config::Simple", "$lbpconfigdir/pluginconfig.cfg";
my $UDP_Port = %pcfg{'MAIN.UDP_Port'};
#$UDP_Send_Enable = %pcfg{'MAIN.UDP_Send_Enable'};
my $HTTP_TEXT_Send_Enable = %pcfg{'MAIN.HTTP_TEXT_Send_Enable'};
my $MINISERVER = %pcfg{'MAIN.MINISERVER'};
%miniservers = LoxBerry::System::get_miniservers();


# Miniserver konfig auslesen
#print "\n".substr($MINISERVER, 10, length($MINISERVER))."\n";
my $i = substr($MINISERVER, 10, length($MINISERVER));
my $LOX_Name = $miniservers{$i}{Name};
my $LOX_IP = $miniservers{$i}{IPAddress};
my $LOX_User = $miniservers{$i}{Admin};
my $LOX_PW = $miniservers{$i}{Pass};

#print "Miniserver\@".$LOX_Name."<br>";
#print $LOX_IP."<br>";
#print $LOX_User."<br>";
#print $LOX_PW."<br>";

# Mit dieser Konstruktion lesen wir uns alle POST-Parameter in den Namespace R.
my $cgi = CGI->new;
$cgi->import_names('R');
# Ab jetzt kann beispielsweise ein POST-Parameter 'form' ausgelesen werden mit $R::form.

# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'cronjob',
	filename => "$lbplogdir/vzug.log",
	append => 1
	);
LOGSTART "V-ZUG set webpage";

# POST request
my $POST_IP = $R::ip;
my $POST_COM = $R::command;
#my $POST_IP = "172.16.200.105";


# UDP-Port Erstellen für Loxone
my $sock = new IO::Socket::INET(PeerAddr => $LOX_IP,
                PeerPort => $UDP_Port,
                Proto => 'udp', Timeout => 1) or die('Error opening socket.');
			

# Loxone HA-Miniserver by Marcel Zoller	
if($LOX_Name eq "lxZoller1"){
	# Loxone Minisever ping test
	LOGOK " Loxone Zoller HA-Miniserver";
	#$LOX_IP="172.16.200.7"; #Testvariable
	#$LOX_IP='172.16.200.6'; #Testvariable
	our $p = Net::Ping->new();
	$p->port_number("80");
	if ($p->ping($LOX_IP,2)) {
				LOGOK "Ping Loxone: Miniserver1 is online.";
				LOGOK "Ping Loxone: $p->ping($LOX_IP)";
				$p->close();
			} else{ 
				LOGALERT "Ping Loxone: Miniserver1 not online!";
				LOGDEB "Ping Loxone: $p->ping($LOX_IP)";
				$p->close();
				
				$p = Net::Ping->new();
				$p->port_number("80");
				$LOX_IP = $miniservers{2}{IPAddress};
				$LOX_User = $miniservers{2}{Admin};
				$LOX_PW = $miniservers{2}{Pass};
				#$LOX_IP="172.16.200.6"; #Testvariable
				if ($p->ping($LOX_IP,2)) {
					LOGOK "Ping Loxone: Miniserver2 is online.";
					LOGOK "Ping Loxone: $p->ping($LOX_IP)";
				} else {
					LOGALERT "Ping Loxone: Miniserver2 not online!";
					LOGDEB "Ping Loxone: $p->ping($LOX_IP)";
					#Failback Variablen !!!
					$LOX_IP = $miniservers{1}{IPAddress};
					$LOX_User = $miniservers{1}{Admin};
					$LOX_PW = $miniservers{1}{Pass};	
				} 
			}
		$p->close();			
}		

my @vzugIP;
# Wenn keine POST, dann alle V-Zug Geräte abfragen

my $hisIP;


my $p;
#$hisIP = '172.16.200.105';

print "<b>IP\@$POST_IP</b><br>";
# Ab hier kommt die Abfrage
	
LOGDEB "Loxone Name: $LOX_Name";

my $dev1ip = $POST_IP;
LOGDEB "V-ZUG IP: $dev1ip";

# API Version Abfragen
# http://172.16.200.158/ai?command=getAPIVersion
# {"value":"1.7.0"}
# Version 1.1.0 ist die alte APIVersion
# Version 1.7.0 ist die neue APIVersion mit Abfrage mit hh?command=getProgram
# http://172.16.200.158/hh?command=getProgram
# [{"id":2500,"name":"Stark trocken","status":"active","duration":{"set":12000,"act":1271},"allowedStatusChanges":{"options":["idle","paused"]}}]
# 
# http://172.16.200.158/hh?command=doTurnOff
# http://172.16.200.105/hh?command=doTurnOff
# 
# http://172.16.200.105/hh?command=setDeviceName&value=' + encodeURIComponent(deviceName)
#
# http://172.16.200.158/hh?command=getZHMode
# {"value":2}
# http://172.16.200.105/ai?command=getModelDescription
# Adora SL
	
my $contentsAPIVersion = get("http://$dev1ip/ai?command=getAPIVersion");
LOGDEB "SEND HTTP: http://$dev1ip/ai?command=getAPIVersion";
LOGDEB "Result HTTP: $contentsAPIVersion";



# HTTP Status vom V-Zug Gerät abfragen und aufteilen
my $contents;
#my $contents = get("http://$dev1ip/hh?command=$POST_COM");
unless (defined ($contents = get("http://$dev1ip/hh?command=$POST_COM"))) {
    die "could not get http://$dev1ip/hh?command=$POST_COM\n";
	LOGDEB "SEND HTTP: http://$dev1ip/hh?command=$POST_COM";
	LOGDEB "Result HTTP: $contents";
} else {
	LOGDEB "SEND HTTP: http://$dev1ip/hh?command=$POST_COM";
	LOGDEB "Result HTTP: $contents";
	print "command $POST_COM send.";
}
# if ($contents eq "") { 
#	# print "Keine V-Zug Device gefunden. Falsche IP oder nicht kompatibel<br>"; 
#	$p = Net::Ping->new();
#	$p->port_number("80");
#	if ($p->ping($dev1ip,2)) {
#			print "$dev1ip is not a V-Zug Device or compatible!<br><br>";
#			LOGALERT "Ping: V-Zug IP ping found, wrong IP or not compatible";
#			LOGDEB "Ping: $p->ping($dev1ip)";
#		} else{ 
#			print "$dev1ip ist not reachable!<br><br>";
#			#print "$p->ping($dev1ip)<br>";
#			LOGALERT "Ping: V-Zug IP ping not found";
#			LOGDEB "Ping: $p->ping($dev1ip)";
#		}
#	$p->close();	
#	}

# We start the log. It will print and store some metadata like time, version numbers
# LOGSTART "V-ZUG cronjob start";
  
# Now we really log, ascending from lowest to highest:
# LOGDEB "This is debugging";                 # Loglevel 7
# LOGINF "Infos in your log";                 # Loglevel 6
# LOGOK "Everything is OK";                   # Loglevel 5
# LOGWARN "Hmmm, seems to be a Warning";      # Loglevel 4
# LOGERR "Error, that's not good";            # Loglevel 3
# LOGCRIT "Critical, no fun";                 # Loglevel 2
# LOGALERT "Alert, ring ring!";               # Loglevel 1
# LOGEMERGE "Emergency, for really really hard issues";   # Loglevel 0
  
LOGEND "Operation finished sucessfully.";
