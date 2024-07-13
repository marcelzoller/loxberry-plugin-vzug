#!/usr/bin/perl

# Einbinden von Module
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
use LoxBerry::JSON;
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
		# Version 1.8.0 ist die neue APIVersion (Stand 13.07.2024)
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
		#
		# http://172.16.200.105/hh?command=getEcoInfo"
		# {"water":{"total":45164,"average":12,"program":16},"energy":{"total":3863,"average":0.9,"program":0.9}}
		# {"energy":{"total":111.699,"lastMonth":18.552,"lastYear":95.566,"average":0.709,"program":0.816}}
		#
		# http://172.16.200.105/hh?command=getDeviceStatus
		# {"errors":[],"displayedErrors":[],"notifications":[],"isUpdatePossible":true}
		# 
		# http://172.16.200.105/ai?command=getCloudStatus
		# {"enabled":true,"claimed":false,"telemetryCollectionEnabled":true,"status":"connected","secTokenValid":true,"scope":"PROD"}
		# 
		# http://172.16.200.105/ai?command=getFWVersion
		# {"fn":"23038 007651","SW":"1052633-R19","SD":"1052633-R19","HW":"1022913-R08","apiVersion":"1.8.0","phy":"WLAN","deviceUuid":"3902409"}

		
		my $contentsAPIVersion = get("http://$dev1ip/ai?command=getAPIVersion");
		LOGDEB "SEND HTTP: http://$dev1ip/ai?command=getAPIVersion";
		LOGDEB "Result HTTP: $contentsAPIVersion";
		
		# HTTP Status Wasser und Energie vom V-Zug Gerät abfragen und aufteilen (Input Samuel Müller)
		my $contentsWasserEnergie = get("http://$dev1ip/hh?command=getEcoInfo");
		LOGDEB "SEND HTTP: http://$dev1ip/hh?command=getEcoInfo";
		LOGDEB "Result HTTP: $contentsWasserEnergie";
		# print "Result HTTP: $contentsWasserEnergie<br>";
		
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

		# {"water":{"total":45164,"average":12,"program":16},"energy":{"total":3863,"average":0.9,"program":0.9}}
		# {"water":{"total":45164,"average":12},"energy":{"total":3863,"average":0.9}}
		# {"energy":{"total":111.699,"lastMonth":18.552,"lastYear":95.566,"average":0.709,"program":0.816}}
		# {"energy":{"total":420.757,"average":0.643,"program":0.845}}

		my @valuesWasserEnergie = split('\"',$contentsWasserEnergie);
		my $WasserTotal = 0;
		my $WasserAverage = 0;
		my $WasserProgram = 0;
		my $EnergyTotal = 0;
		my $EnergyAverage = 0;
		my $EnergyProgram = 0;
		
		# Wasser Daten Adora SL
		$Wasser = $valuesWasserEnergie[1];
		if($Wasser eq "water"){
			if($valuesWasserEnergie[3] eq "total"){
				$WasserTotal = $valuesWasserEnergie[4];
				$WasserTotal =~ s/\://g;
				$WasserTotal =~ s/\,//g;		
				$WasserTotal =~ s/\}//g;
			}
			if($valuesWasserEnergie[5] eq "average"){
				$WasserAverage = $valuesWasserEnergie[6];
				$WasserAverage =~ s/\://g;
				$WasserAverage =~ s/\,//g;		
				$WasserAverage =~ s/\}//g;
			}
			if($valuesWasserEnergie[7] eq "program"){
				$WasserProgram = $valuesWasserEnergie[8];
				$WasserProgram =~ s/\://g;
				$WasserProgram =~ s/\,//g;
				$WasserProgram =~ s/\}//g;
			}
		}
		# Energy Daten Adora SL
		$Energy = $valuesWasserEnergie[9];
		if($Energy eq "energy"){
			if($valuesWasserEnergie[11] eq "total"){
				$EnergyTotal = $valuesWasserEnergie[12];
				$EnergyTotal =~ s/\://g;
				$EnergyTotal =~ s/\,//g;
				$EnergyTotal =~ s/\}//g;
			}
			if($valuesWasserEnergie[13] eq "average"){
				$EnergyAverage = $valuesWasserEnergie[14];
				$EnergyAverage =~ s/\://g;
				$EnergyAverage =~ s/\,//g;		
				$EnergyAverage =~ s/\}//g;
			}
			if($valuesWasserEnergie[15] eq "program"){
				$EnergyProgram = $valuesWasserEnergie[16];
				$EnergyProgram =~ s/\://g;
				$EnergyProgram =~ s/\,//g;
				$EnergyProgram =~ s/\}//g;
			}
		}
		# Energy Daten CombiSteamer & Dry
		#  {"energy":{"total":111.699,"lastMonth":18.552,"lastYear":95.566,"average":0.709,"program":0.816}}
		$Energy = $valuesWasserEnergie[1];
		if($Energy eq "energy"){
			if($valuesWasserEnergie[3] eq "total"){
				$EnergyTotal = $valuesWasserEnergie[4];
				$EnergyTotal =~ s/\://g;
				$EnergyTotal =~ s/\,//g;
				$EnergyTotal =~ s/\}//g;
			}
			if($valuesWasserEnergie[5] eq "average"){	
				$EnergyAverage = $valuesWasserEnergie[6];
				$EnergyAverage =~ s/\://g;
				$EnergyAverage =~ s/\,//g;
				$EnergyAverage =~ s/\}//g;
			}
			if($valuesWasserEnergie[9] eq "average"){	
				$EnergyAverage = $valuesWasserEnergie[10];
				$EnergyAverage =~ s/\://g;
				$EnergyAverage =~ s/\,//g;
				$EnergyAverage =~ s/\}//g;
			}
			if($valuesWasserEnergie[11] eq "program"){	
				$EnergyProgram = $valuesWasserEnergie[12];
				$EnergyProgram =~ s/\://g;
				$EnergyProgram =~ s/\,//g;
				$EnergyProgram =~ s/\}//g;
			}
		}
		# Wenn kein Wert, dann 0 abfüllen
		if($WasserTotal  eq "") {	$WasserTotal="0"; }	
		if($WasserAverage  eq "") {	$WasserAverage="0"; }
		if($WasserProgram  eq "") {	$WasserProgram="0"; }
		if($EnergyTotal  eq "") {	$EnergyTotal="0"; }	
		if($EnergyAverage  eq "") {	$EnergyAverage="0"; }
		if($EnergyProgram  eq "") {	$EnergyProgram="0"; }




		print "DeviceName$k\@$DeviceNameStr<br>";
		print "APIVersion$k\@$DeviceAPIVersionStr<br>";
		print "Serial$k\@$SerialStr<br>";
		print "Program$k\@$ProgrammStr<br>";
		print "Status$k\@$StatusStr<br>";
		print "Time$k\@$ZeitStr<br>";
		print "Min$k\@$MinStr<br>";
		print "WasserTotal$k\@$WasserTotal<br>";
		print "WasserAverage$k\@$WasserAverage<br>";
		print "WasserProgram$k\@$WasserProgram<br>";
		print "EnergyTotal$k\@$EnergyTotal<br>";
		print "EnergyAverage$k\@$EnergyAverage<br>";
		print "EnergyProgram$k\@$EnergyProgram<br><br>";
	

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
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterTotal/$WasserTotal");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterAverage/$WasserAverage");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterProgram/$WasserProgram");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyTotal/$EnergyTotal");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyAverage/$EnergyAverage");
			$contents = get("http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyProgram/$EnergyProgram");
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Status/$StatusStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Program/$ProgrammStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Time/$ZeitStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Min/$MinStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Devicename/$DeviceNameStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_Serial/$SerialStr";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterTotal/$WasserTotal";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterAverage/$WasserAverage";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_WaterProgram/$WasserProgram";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyTotal/$EnergyTotal";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyAverage/$EnergyAverage";
			LOGDEB "URL: http://$LOX_User:$LOX_PW\@$LOX_IP/dev/sps/io/VZUG_Device${k}_EnergyProgram/$EnergyProgram";
			}
		else {
			LOGDEB "HTTP_TEXT_Send_Enable: 0";
		}
			
		if ($UDP_Send_Enable == 1) {
			print $sock "DeviceName$k\@$DeviceNameStr\; Serial$k\@$SerialStr\; Program$k\@$ProgrammStr\; Status$k\@$StatusStr\; Time$k\@$ZeitStr; Min$k\@$MinStr; WaterTotal$k\@$WasserTotal; WaterAverage$k\@$WasserAverage; WaterProgram$k\@$WasserProgram; EnergyTotal$k\@$EnergyTotal; EnergyAverage$k\@$EnergyAverage; EnergyProgram$k\@$EnergyProgramProgram";
			LOGDEB "Loxone IP: $LOX_IP";

			LOGDEB "UDP Port: $UDP_Port";
			LOGDEB "UDP Send: DeviceName$k\@$DeviceNameStr\; Serial$k\@$SerialStr\; Program$k\@$ProgrammStr\; Status$k\@$StatusStr\; Time$k\@$ZeitStr; Min$k\@$MinStr; WaterTotal$k\@$WasserTotal; WaterAverage$k\@$WasserAverage; WaterProgram$k\@$WasserProgram; EnergyTotal$k\@$EnergyTotal; EnergyAverage$k\@$EnergyAverage; EnergyProgram$k\@$EnergyProgram";

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
