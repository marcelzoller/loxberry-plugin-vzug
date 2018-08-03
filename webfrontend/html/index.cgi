#!/usr/bin/perl

# Einbinden von Module
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use IO::Socket::INET;
use LWP::Simple;
use Net::Ping;


print "Content-type: text/html\n\n";

# Konfig auslesen
my %pcfg;
my %miniservers;
tie %pcfg, "Config::Simple", "$lbpconfigdir/pluginconfig.cfg";
$UDP_Port = %pcfg{'MAIN.UDP_Port'};
$UDP_Send_Enable = %pcfg{'MAIN.UDP_Send_Enable'};
%miniservers = LoxBerry::System::get_miniservers();
$LOX_IP = $miniservers{1}{IPAddress};

# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'cronjob',
	filename => "$lbplogdir/vzug.log",
	append => 1
	);
LOGSTART "V-ZUG cronjob start";

# UDP-Port Erstellen für Loxone
my $sock = new IO::Socket::INET(PeerAddr => $LOX_IP,
                PeerPort => $UDP_Port,
                Proto => 'udp', Timeout => 1) or die('Error opening socket.');
			
				
$dev1ip = %pcfg{'Device1.IP'};
LOGDEB "Z-ZUG IP: $dev1ip";
# HTTP Status vom V-Zug Gerät abfragen und aufteilen
$contents = get("http://$dev1ip/ai?command=getDeviceStatus");
LOGDEB "SEND HTTP: http://$dev1ip/ai?command=getDeviceStatus";
LOGDEB "Result HTTP: $contents";
if ($contents eq "") { 
	# print "Keine V-Zug Device gefunden. Falsche IP oder nicht kompatibel<br>"; 
	$p = Net::Ping->new();
	if ($p->ping($dev1ip,1)) {
			print "$dev1ip is not a V-Zug Device or compatible!<br><br>";
			LOGALERT "Ping: V-Zug IP ping found, wrong IP or not compatible";
		} else{ 
			print "$dev1ip ist not reachable!<br><br>";
			#print "$p->ping($dev1ip)<br>";
			LOGALERT "Ping: V-Zug IP ping not found";
			LOGDEB "Ping: $p->ping($dev1ip)";
		}
    $p->close();

	
	}
	
	

	
my @values = split('\"', $contents);

# Werte aus dem Result auswerten und in Variablen schreiben
$DeviceNameStr = $values[3];
$SerialStr = $values[7];
$ProgrammStr = $values[15];
$StatusStr = $values[19];
# $StatusStr = StatusStr.replace('\n',' ')
$StatusStr =~ tr/\\n/ /;
$ZeitStr = $values[25];

# Wenn kein Programm läuft beim V-Zug, einfach einen - setzten.
if ($StatusStr =~ m//) {    $StatusStr="-";  }
if ($ProgrammStr =~ m//) {    $ProgrammStr="-";  }
if ($ZeitStr =~ m//) {    $ZeitStr="-";  }

print "DeviceName1\@$DeviceNameStr<br>";
print "Serial1\@$SerialStr<br>";
print "Program1\@$ProgrammStr<br>";
print "Status1\@$StatusStr<br>";
print "Time1\@$ZeitStr<br>";

if ($UDP_Send_Enable == 1) {
	print $sock "DeviceName1\@$DeviceNameStr\; Serial1\@$SerialStr\; Program1\@$ProgrammStr\; Status1\@$StatusStr\; Time1\@$ZeitStr";
	LOGDEB "Loxone IP: $LOX_IP";
	LOGDEB "UDP Port: $UDP_Port";
	LOGDEB "UDP Send: DeviceName1\@$DeviceNameStr\; Serial1\@$SerialStr\; Program1\@$ProgrammStr\; Status1\@$StatusStr\; Time1\@$ZeitStr";
	}

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
