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
LOGSTART "V-ZUG scan webpage";

# POST request
my $POST_IP = $R::ip;
my $POST_DevName = $R::DeviceName;
#my $POST_IP = "172.16.200.105";
if($POST_DevName eq ""){
	$POST_DevName="Device1";	
}
print "$POST_DevName<br>";

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
# Wenn keine POST, dann alle Magic Home Controller abfragen

my $hisIP;

if($POST_IP==""){
	# V-ZUG Status IP 
	LOGDEB "Broadcast Scan nach V-Zug Geräten";
	#print "leer<br>";
	

	# Hier startet der SCAN (Broadcast)
	my($sock, $server_host, $msg,$msg1, $port, $ipaddr, $hishost,$hisIP, $iaddr, $TIMEOUT, $recvmsg, $mysockport);
	my $server_host = '255.255.255.255';
	my $msg         = "DISCOVERY_LAN_INTERFACE_REQUEST";
	my $sock = IO::Socket::INET->new(   Proto     => 'udp',
										PeerPort  => 2047,
										PeerAddr  => $server_host,
										Type      => SOCK_DGRAM,
										Broadcast => 1    )
		or die "Creating socket: $!\n";

	$sock->send($msg) or die "send: $!";
	my $mysockport = $sock->sockport();
	$sock->close();

	my $sock = IO::Socket::INET->new(   LocalPort => $mysockport,
										Type => SOCK_DGRAM, 
										Proto => 'udp',
										timeout => 3    )
		or die "socket: $@";

	# V-ZUG Anrwort MSG auf Broadcast
	$msg         = "DISCOVERY_LAN_INTERFACE_RESPONSE";
	
	#Timeout 5s recevie data
	eval {
		local $SIG{ALRM} = sub { die 'Timed Out'; };
		alarm 5;

		while(1){
				$sock->recv($recvmsg, 1024);
		
				my($port, $ipaddr) = sockaddr_in($sock->peername);
				#printf("%s\n",$sock->peerhost);
				$hisIP = $sock->peerhost;
				my $hishost = gethostbyaddr($ipaddr, AF_INET);
				#print "Client $hishost or $hisIP said '$recvmsg'\n";
				if($recvmsg eq $msg) {
					#push @vzugIP, $hisIP;
					#push @vzugIP, $hisIP;
					push @vzugIP, $hisIP;
				}   
		} 
		alarm 0;
	};
} else {
	# V-ZUG Status IP 
	LOGDEB "Request Post $POST_IP";
	push @vzugIP, $POST_IP;
}

my $p;
#$hisIP = '172.16.200.105';
foreach my $n (@vzugIP){
	print "<b>IP\@$n</b><br>";
	#print "DevName $POST_DevName<br>";
	# Ab hier kommt die Abfrage
		
	LOGDEB "Loxone Name: $LOX_Name";			
	#$dev1ip = %pcfg{'Device1.IP'};
	my $dev1ip = $n;
	LOGDEB "V-ZUG IP: $dev1ip";
	# HTTP Status vom V-Zug Gerät abfragen und aufteilen
	my $contents = get("http://$dev1ip/ai?command=getDeviceStatus");
	LOGDEB "SEND HTTP: http://$dev1ip/ai?command=getDeviceStatus";
	LOGDEB "Result HTTP: $contents";
	if ($contents eq "") { 
		# print "Keine V-Zug Device gefunden. Falsche IP oder nicht kompatibel<br>"; 
		$p = Net::Ping->new();
		$p->port_number("80");
		if ($p->ping($dev1ip,2)) {
				print "$dev1ip is not a V-Zug Device or compatible!<br><br>";
				LOGALERT "Ping: V-Zug IP ping found, wrong IP or not compatible";
				LOGDEB "Ping: $p->ping($dev1ip)";
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
	my $DeviceNameStr = $values[3];
	my $SerialStr = $values[7];
	my $ProgrammStr = $values[15];
	my $StatusStr = $values[19];
	# Ersetzte \n durch ein leerzeichen
	my $StatusStr =~ s/\n/ /g; 
	my $ZeitStr = $values[25];

	# Wenn kein Programm läuft beim V-Zug, einfach einen - setzten.
	# if ($StatusStr =~ m//) {    $StatusStr="-";  }
	# if ($ProgrammStr =~ m//) {    $ProgrammStr="-";  }
	# if ($ZeitStr =~ m//) {    $ZeitStr="-";  }
	if ($StatusStr eq "") {    $StatusStr="-";  }
	if ($ProgrammStr eq "") {    $ProgrammStr="-";  }
	if ($ZeitStr eq "") {    $ZeitStr="-";  }

	print "DeviceName\@$DeviceNameStr<br>";
	print "Serial\@$SerialStr<br>";
	print "Program\@$ProgrammStr<br>";
	print "Status\@$StatusStr<br>";
	print "Time\@$ZeitStr<br>";


	# $ProgrammStr = "test";
	# $StatusStr = "läuft";
	# $ZeitStr = "2:12";

	# Immer via HTTP schicken - Gateway Webseite
	$HTTP_TEXT_Send_Enable = 1;
	if ($HTTP_TEXT_Send_Enable == 1) {
		LOGDEB "Loxone IP: $LOX_IP";
		LOGDEB "User: $LOX_User";
		LOGDEB "Password: $LOX_PW";
		# wgetstr = "wget --quiet --output-document=temp http://"+loxuser+":"+loxpw+"@"+loxip+"/dev/sps/io/VZUG_Adora_Programm/" + str(ProgrammStr) 
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Status/$StatusStr");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Program/$ProgrammStr");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Time/$ZeitStr");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Devicename/$DeviceNameStr");
		$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Serial/$SerialStr");
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Status/$StatusStr";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Program/$ProgrammStr";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Time/$ZeitStr";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Devicename/$DeviceNameStr";
		LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_$POST_DevName\_Serial/$SerialStr";
		}
	else {
		LOGDEB "HTTP_TEXT_Send_Enable: 0";
	}
		
	#if ($UDP_Send_Enable == 1) {
	#	print $sock "DeviceName1\@$DeviceNameStr\; Serial1\@$SerialStr\; Program1\@$ProgrammStr\; Status1\@$StatusStr\; Time1\@$ZeitStr";
	#	LOGDEB "Loxone IP: $LOX_IP";
#
#		LOGDEB "UDP Port: $UDP_Port";
#		LOGDEB "UDP Send: DeviceName1\@$DeviceNameStr\; Serial1\@$SerialStr\; Program1\@$ProgrammStr\; Status1\@$StatusStr\; Time1\@$ZeitStr";
#		}

	
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
