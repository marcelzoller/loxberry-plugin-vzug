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
#$UDP_Send_Enable = %pcfg{'MAIN.UDP_Send_Enable'};
$HTTP_TEXT_Send_Enable = %pcfg{'MAIN.HTTP_TEXT_Send_Enable'};
$MINISERVER = %pcfg{'MAIN.MINISERVER'};
%miniservers = LoxBerry::System::get_miniservers();


# Miniserver konfig auslesen
#print "\n".substr($MINISERVER, 10, length($MINISERVER))."\n";
$i = substr($MINISERVER, 10, length($MINISERVER));
$LOX_Name = $miniservers{$i}{Name};
$LOX_IP = $miniservers{$i}{IPAddress};
$LOX_User = $miniservers{$i}{Admin};
$LOX_PW = $miniservers{$i}{Pass};

print "Miniserver\@".$LOX_Name."<br>";
#print $LOX_IP."<br>";
#print $LOX_User."<br>";
#print $LOX_PW."<br>";

# Mit dieser Konstruktion lesen wir uns alle POST-Parameter in den Namespace R.
my $cgi = CGI->new;
$cgi->import_names('R');
# Ab jetzt kann beispielsweise ein POST-Parameter 'form' ausgelesen werden mit $R::form.


# POST request
$VZug_IP = $R::ip;
# $VZug_IP = "172.16.200.105";



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
			

# Loxone HA-Miniserver by Marcel Zoller	
if($LOX_Name eq "lxZoller1"){
	# Loxone Minisever ping test
	LOGOK " Loxone Zoller HA-Miniserver";
	#$LOX_IP="172.16.200.7"; #Testvariable
	#$LOX_IP='172.16.200.6'; #Testvariable
	$p = Net::Ping->new();
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
# Alle VZUG IPs aus der Konfig
my $hisIP;	
my $k;
my $anzahl=4;
if ($VZug_IP ne "") {
		$anzahl = 1;
	}
for (my $i=0; $i < $anzahl; $i++) {
	$k = $i+1;
	$dev1ip = %pcfg{"Device$k.IP"};
	push @vzugIP, $dev1ip;
	#print "$vzugIP[$i]<br>";

	LOGDEB "Loxone Name: $LOX_Name";			
	# $dev1ip = %pcfg{'Device1.IP'};
	if ($VZug_IP ne "") {
		$dev1ip = $VZug_IP;
	}
	
	if ($dev1ip ne "") {
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
		# http://172.16.200.105/ai?command=getLastPUSHNotifications
		# [{"date":"2021-06-01T02:33:55","message":"Programm Eco-Programm gestartet"} ,{"date":"2021-05-31T22:31:38","message":"Programm Automatik beendet - Energie: <0,1 kWh, Wasser: 0 ℓ"} ,{"date":"2021-05-31T21:59:34","message":"Programm Eco-Programm beendet - Energie: <0,1 kWh, Wasser: 0 ℓ"} ]
		# http://172.16.200.105/hh?command=setProgram&value=%7B%22id%22:50%7D    // URL decode {"id":50}
		# setProgram
		# id: 50 = Eco Modus
		# id: 51 = Auto
		# id: 52 = ALltag Kurz
		# id: 53 = Sprint
		# id: 54 = Intensiv
		# id: 55 = Silent
		# id: 56 = Patry
		# id: 57 = Glas
		# id: 58 = Fondue / Raclette
		# id: 59 = Hygiene
		# id: 61 = Vorspülen
		# http://172.16.200.105/hh?command=setProgram&value=%7B%22partialload%22:false,%22eco%22:%22none%22,%22steamfinish%22:false%7D
		#
		# http://172.16.200.105/hh?command=setProgram&value={"partialload":true,"steamfinish":true,"eco":"optiStart"}
		# eco: energySaving
		# eco: optiStart
		# eco: none
		# steamfinish: true / false
		# partialload: true / false

		
		my $contentsAPIVersion = get("http://$dev1ip/ai?command=getAPIVersion");
		LOGDEB "SEND HTTP: http://$dev1ip/ai?command=getAPIVersion";
		LOGDEB "Result HTTP: $contentsAPIVersion";
		

		# HTTP Status vom V-Zug Gerät abfragen und aufteilen
		$contents = get("http://$dev1ip/ai?command=getDeviceStatus");
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
					print "$dev1ip ist not reachable!<br>";
					#print "$p->ping($dev1ip)<br>";
					LOGALERT "Ping: V-Zug IP ping not found";
					LOGDEB "Ping: $p->ping($dev1ip)";
				}
			$p->close();
			}
		
		my @values = split('\"',$contentsAPIVersion);
		$DeviceAPIVersionStr= $values[3];
		
		my @values = split('\"', $contents);

		# Werte aus dem Result auswerten und in Variablen schreiben
		$DeviceNameStr = $values[3];
		$SerialStr = $values[7];
		$ProgrammStr = $values[15];
		$StatusStr = $values[19];
		# Ersetzte \n durch ein leerzeichen - leerzeichen
		$StatusStr =~ s/\\n/ - /; 
	
		$ZeitStr = $values[25];
		
		# $ProgrammStr = "test";
		# $StatusStr = "läuft";
		# $ZeitStr = "2h12";
		
		
		# Wenn kein Programm läuft beim V-Zug, einfach einen - setzten.
		if ($StatusStr eq "") {    $StatusStr="-";  }

	
		if ($ProgrammStr eq "") {    $ProgrammStr="-";  }
		# $ZeitStr="3h22";
		if ($ZeitStr eq "") {    
				$ZeitStr="-";  
				$MinStr ="0";
				# print "VZug Programm fertig<br>";
			} else {
				my @words = split /h/, $ZeitStr;
				$MinStr=$words[0]*60+$words[1]; 
				
			}


		print "DeviceName$k\@$DeviceNameStr<br>";
		print "APIVersion$k\@$DeviceAPIVersionStr<br>";
		print "Serial$k\@$SerialStr<br>";
		print "Program$k\@$ProgrammStr<br>";
		print "Status$k\@$StatusStr<br>";
		print "Time$k\@$ZeitStr<br>";
		print "Min$k\@$MinStr<br><br>";
	

		if ($HTTP_TEXT_Send_Enable == 1) {
			LOGDEB "Loxone IP: $LOX_IP";
			LOGDEB "User: $LOX_User";
			LOGDEB "Password: $LOX_PW";
			# wgetstr = "wget --quiet --output-document=temp http://"+loxuser+":"+loxpw+"@"+loxip+"/dev/sps/io/VZUG_Adora_Programm/" + str(ProgrammStr) 
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Status/$StatusStr");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Program/$ProgrammStr");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Time/$ZeitStr");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Min/$MinStr");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Devicename/$DeviceNameStr");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Serial/$SerialStr");
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Status/$StatusStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Program/$ProgrammStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Time/$ZeitStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Min/$MinStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Devicename/$DeviceNameStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Serial/$SerialStr";
			}
		else {
			LOGDEB "HTTP_TEXT_Send_Enable: 0";
		}
			
		if ($UDP_Send_Enable == 1) {
			print $sock "DeviceName$k\@$DeviceNameStr\; Serial$k\@$SerialStr\; Program$k\@$ProgrammStr\; Status$k\@$StatusStr\; Time$k\@$ZeitStr; Min$k\@$MinStr";
			LOGDEB "Loxone IP: $LOX_IP";

			LOGDEB "UDP Port: $UDP_Port";
			LOGDEB "UDP Send: DeviceName$k\@$DeviceNameStr\; Serial$k\@$SerialStr\; Program$k\@$ProgrammStr\; Status$k\@$StatusStr\; Time$k\@$ZeitStr; Min$k\@$MinStr";

		}
	}
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
