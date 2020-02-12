#!/usr/bin/perl


##########################################################################
# LoxBerry-Module
##########################################################################
use CGI;
use LoxBerry::System;
use LoxBerry::Web;
use LoxBerry::Log;
  
# Die Version des Plugins wird direkt aus der Plugin-Datenbank gelesen.
my $version = LoxBerry::System::pluginversion();

# Loxone Miniserver Select Liste Variable
our $MSselectlist;

# Mit dieser Konstruktion lesen wir uns alle POST-Parameter in den Namespace R.
my $cgi = CGI->new;
$cgi->import_names('R');
# Ab jetzt kann beispielsweise ein POST-Parameter 'form' ausgelesen werden mit $R::form.

# Create my logging object
my $log = LoxBerry::Log->new ( 
	name => 'HTTP Settup',
	filename => "$lbplogdir/vzug.log",
	append => 1
	);
LOGSTART "V-ZUG HTTP start";
 
 
# Wir Übergeben die Titelzeile (mit Versionsnummer), einen Link ins Wiki und das Hilfe-Template.
# Um die Sprache der Hilfe brauchen wir uns im Code nicht weiter zu kümmern.
LoxBerry::Web::lbheader("V-ZUG Plugin V$version", "http://www.loxwiki.eu/V-Zug/Zoller", "help.html");
  
# Wir holen uns die Plugin-Config in den Hash %pcfg. Damit kannst du die Parameter mit $pcfg{'Section.Label'} direkt auslesen.
my %pcfg;
tie %pcfg, "Config::Simple", "$lbpconfigdir/pluginconfig.cfg";

# Alle Miniserver aus Loxberry config auslesen
%miniservers = LoxBerry::System::get_miniservers();

 

# Wir initialisieren unser Template. Der Pfad zum Templateverzeichnis steht in der globalen Variable $lbptemplatedir.

my $template = HTML::Template->new(
    filename => "$lbptemplatedir/index.html",
    global_vars => 1,
    loop_context_vars => 1,
    die_on_bad_params => 0,
	associate => $cgi,
);
  

# Sprachdatei laden
my %L = LoxBerry::Web::readlanguage($template, "language.ini");
  


##########################################################################
# Process form data
##########################################################################
if ($cgi->param("save")) {
	# Data were posted - save 
	&save;
}
	

# print "Geräte Name: <i>" . %pcfg{'Device1.NAME'} . "</i><br>\n";
# print "Geräte IP: <i>" . %pcfg{'Device1.IP'} . "</i><br>\n";
my $IP1 = %pcfg{'Device1.IP'};
my $IP2 = %pcfg{'Device2.IP'};
my $IP3 = %pcfg{'Device3.IP'};
my $IP4 = %pcfg{'Device4.IP'};
my $UDPPORT = %pcfg{'MAIN.UDP_Port'};
my $UDPSEND = %pcfg{'MAIN.UDP_Send_Enable'};
my $UDPSENDINTER = %pcfg{'MAIN.UDP_SEND_Intervall'};
my $HTTPSEND = %pcfg{'MAIN.HTTP_TEXT_Send_Enable'};
my $HTTPSENDINTER = %pcfg{'MAIN.HTTP_TEXT_SEND_Intervall'};
my $miniserver = %pcfg{'MAIN.MINISERVER'};

%miniservers = LoxBerry::System::get_miniservers();
#print "Anzahl deiner Miniserver: " . keys(%miniservers);

##########################################################################
# Fill Miniserver selection dropdown
##########################################################################
for (my $i = 1; $i <=  keys(%miniservers);$i++) {
	if ("MINISERVER$i" eq $miniserver) {
		$MSselectlist .= '<option selected value="'.$i.'">'.$miniservers{$i}{Name}."</option>\n";
	} else {
		$MSselectlist .= '<option value="'.$i.'">'.$miniservers{$i}{Name}."</option>\n";
	}
}

$template->param( IP1 => $IP1);
$template->param( IP2 => $IP2);
$template->param( IP3 => $IP3);
$template->param( IP4 => $IP4);
$template->param(LOXLIST => $MSselectlist);
$template->param( UDPPORT => $UDPPORT);
$template->param( WEBSITE => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi");
$template->param( LOGDATEI => "/admin/system/tools/logfile.cgi?logfile=plugins/$lbpplugindir/vzug.log&header=html&format=template");
$template->param( WEBSTATUS => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/status.cgi");
$template->param( WEBIP1 => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?ip=$IP1");
$template->param( WEBIP2 => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?ip=$IP2");
$template->param( WEBIP3 => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?ip=$IP3");
$template->param( WEBIP4 => "http://$ENV{HTTP_HOST}/plugins/$lbpplugindir/index.cgi?ip=$IP4");
#$template->param( PNAME => "V-Zug");
#$template->param( LBIP => "172.16.200.66");
if ($UDPSEND == 1) {
		$template->param( UDPSEND => "checked");
		$template->param( UDPSENDYES => "selected");
		$template->param( UDPSENDNO => "");
	} else {
		$template->param( UDPSEND => " ");
		$template->param( UDPSENDYES => "");
		$template->param( UDPSENDNO => "selected");
	} 
if ($HTTPSEND == 1) {
		$template->param( HTTPSEND => "checked");
		$template->param( HTTPSENDYES => "selected");
		$template->param( HTTPSENDNO => "");
	} else {
		$template->param( HTTPSEND => " ");
		$template->param( HTTPSENDYES => "");
		$template->param( HTTPSENDNO => "selected");
	} 

  
 
  
# Nun wird das Template ausgegeben.
print $template->output();
  
# Schlussendlich lassen wir noch den Footer ausgeben.
LoxBerry::Web::lbfooter();

LOGEND "V-ZUG Setting finish.";

##########################################################################
# Save data
##########################################################################
sub save 
{

	# We import all variables to the R (=result) namespace
	$cgi->import_names('R');
	
	# print "DEV1:$R::Dev1<br>\n";
	# print "UDP_Port:$R::UDP_Port<br>\n";
	# print "UDP_Send:$R::UDP_Send<br>\n";
	# print "UDP_Sendddd:$R::UDP_Send<br>\n";
	LOGDEB "UDP Port: $R::UDP_Port";
	

	if ($R::Dev1 != "") {
			#print "DEV1:$R::Dev1<br>\n";
			$pcfg{'Device1.IP'} = $R::Dev1;
			# tied(%pcfg)->write();
		}
	if ($R::Dev1 eq "") {
			# print "DEV1:$R::Dev1<br>\n";
			$pcfg{'Device1.IP'} = "";
		}
	if ($R::Dev2 != "") {
			# print "DEV2:$R::Dev2<br>\n";
			$pcfg{'Device2.IP'} = $R::Dev2;
			# tied(%pcfg)->write();
		}
	if ($R::Dev2 eq "") {
			# print "DEV2:$R::Dev2<br>\n";
			$pcfg{'Device2.IP'} = "";
			# tied(%pcfg)->write();
		}
	if ($R::Dev3 != "") {
			# print "DEV3:$R::Dev3<br>\n";
			$pcfg{'Device3.IP'} = $R::Dev3;
			# tied(%pcfg)->write();
		}
	if ($R::Dev3 eq "") {
			# print "DEV3:$R::Dev3<br>\n";
			$pcfg{'Device3.IP'} = "";
		}
	if ($R::Dev4 != "") {
			# print "DEV4:$R::Dev4<br>\n";
			$pcfg{'Device4.IP'} = $R::Dev4;
			# tied(%pcfg)->write();
		}
	if ($R::Dev4 eq "") {
			# print "DEV4:$R::Dev4<br>\n";
			$pcfg{'Device4.IP'} = "";
		}
	if ($R::miniserver != "") {
			#print "miniserver:$R::miniserver<br>\n";
			$pcfg{'MAIN.MINISERVER'} = "MINISERVER".$R::miniserver;
			# tied(%pcfg)->write();
		} 
	if ($R::UDP_Port != "") {
			#print "UDP_Port:$R::UDP_Port<br>\n";
			$pcfg{'MAIN.UDP_Port'} = $R::UDP_Port;
			# tied(%pcfg)->write();
		} 
	if ($R::UDP_Send == "1") {
			LOGDEB "UDP Send: $R::UDP_Send";
			$pcfg{'MAIN.UDP_Send_Enable'} = "1";
			# tied(%pcfg)->write();
		} else{
			LOGDEB "UDP Send: $R::UDP_Send";
			$pcfg{'MAIN.UDP_Send_Enable'} = "0";
			# tied(%pcfg)->write();
		}
		
	if ($R::HTTP_Send == "1") {
			LOGDEB "HTTP Send: $R::HTTP_TEXT_Send";
			$pcfg{'MAIN.HTTP_TEXT_Send_Enable'} = "1";
			# tied(%pcfg)->write();
		} else{
			LOGDEB "HTTP Send: $R::HTTP_TEXT_Send";
			$pcfg{'MAIN.HTTP_TEXT_Send_Enable'} = "0";
			# tied(%pcfg)->write();
		}
	
	tied(%pcfg)->write();
	LOGDEB "Setting: SAVE!!!!";
	#	print "SAVE!!!!";	
	return;
	
}

