import sqlite3
import serial
import time
import datetime

DATABASE_FILE = "maglock.db" #can be a full path to where ever, needs file name too
PIN_ENTRY_TIMEOUT = 5 #in seconds
PIN_MIN_LENGTH = 7


#HEARTBEAT = "HEARTBEAT"
CONTROL_CARD = "0000000"
# red blue green red
CONTROL_PIN = "0000000"



def init_maglockdb():
	rows = select_maglockdb("SELECT name FROM sqlite_master WHERE type='table'")
	
	people_exists = False
	log_exists = False
	
	for row in rows:
		if row[0] == "people":
			print "People table exists!"
			people_exists = True
		if row[0] == "log":
			print "Log table exists!"
			log_exists = True
			
	if (people_exists == False):
		print "People table doesn't exist, creating..."
		commit_maglockdb('''create table people
							(id integer primary key, card text, pin text, date_created text)''')
		
			
	if (log_exists == False):
		print "Log table doesn't exist, creating..."
		commit_maglockdb('''create table log
							(id integer primary key, people_id integer, datestamp text)''')
							

	
def commit_maglockdb(q,data=None):
	conn = sqlite3.connect(DATABASE_FILE)

	c = conn.cursor()
	if data != None:
		c.execute(q,data)
	else:
		c.execute(q)

	c.close()
	conn.commit()
	conn.close()
	


def select_maglockdb(q, data = None):
	conn = sqlite3.connect(DATABASE_FILE)

	c = conn.cursor()
	if data == None:
		c.execute(q)
	else:
		c.execute(q,data)
	
	rows = c.fetchall()
	
	c.close()
	conn.close()
	return rows

def create_user(card, pin):
	# Larger example
	ret = True
	userExists = lookup_user(card)
	if userExists != []:
		ret = False
	else:
		data = (card, pin, str(datetime.datetime.now()))
		commit_maglockdb('insert into people (card,pin,date_created) values (?,?,?)', data)
	
	return ret

def lookup_user(card):
	data = (card,)
	return select_maglockdb("SELECT * FROM people WHERE card=?",data)

def update_user_pin(card,oldpin,newpin):
	userExists = lookup_user(card)
	ret = True
	
	if userExists == []:
		ret = False
	else:
		data = (newpin,card,oldpin)
		commit_maglockdb('UPDATE people SET pin=? WHERE card=? AND pin=?',data)
	
	return ret
	
def delete_user(card):
	userExists = lookup_user(card)
	ret = True
	
	if userExists == []:
		ret = False
	else:
		data = (card,)
		commit_maglockdb('DELETE FROM people WHERE card=?',data)
	
	return ret

def get_all_users():
	return select_maglockdb("SELECT * FROM people")

def init_serial(port):
	#This will change depending on your setup,
	#*nix/windows and which port you have the 'duino plugged into
	PORT = port
	BAUDRATE = 9600
	timeout = 1
	#THE TIMEOUT IS THE MOST IMPORTANT PART
	SER = serial.Serial(port=PORT, baudrate=BAUDRATE,timeout=timeout)

	#Found this as recommended to try and get the serial port back if it's busy
	#doesn't seem to really help though
	SER.close()
	SER.open()

	#Read it was recommended to let the arudino
	#get booted before trying to talk to it
	time.sleep(1.5)
	return SER

def process_serial(val):
	ret = False
	if val.count(":") == 1:
		val = val.replace("\r","")
		val = val.replace("\n","")
		tokens = val.split(":")
		if tokens[0].count("CARD") == 1:
			if tokens[0] == "26CARD":
				ret = tokens
			#Other card formats could go here
			else:
				pass
		elif tokens[0].count("KEY") == 1:
			ret = tokens
		else:
			#unknown format
			pass
	else:
		#unknown format
		pass
		
	return ret


def control_read_loop(ser):
	
	waitingForCard = True
	updatingPin = False
	enteringNewPin = False
	currentCard = ""
	currentPin = ""
	currentUser = None
	oldUserPin = ""
	print "Entering card entry mode, scan a card and then enter a pin to create a new user"
	
	while True:
		val = ser.readline()
		serialData = process_serial(val)
		
		if serialData != False:
			
			if waitingForCard == True:
				
				if serialData[0] == "26CARD":
					
					if serialData[1] == CONTROL_CARD:
						print "The master... HAS LEFT."
						break
					else:
						currentCard = serialData[1]
						print "Read in card: " + currentCard
						currentUser = lookup_user(currentCard)
						if currentUser == []:
							waitingForCard = False
							print "Now enter a pin code for this card..."
						else:
							currentUser = currentUser[0]
							updatingPin = True
							waitingForCard = False
							print "Card already exists in DB.\nEnter current pin to set a new pin, * to delete user, or # to go back to card entry mode."
					
					
				elif serialData[0] == "KEY" and serialData[1] == "11":
					print "The master... HAS LEFT."
					break
				
				else:
					#unrecognized card format, ignoring
					pass
					
			else:
				
				if serialData[0] == "KEY":
					
					if serialData[1] == "10":
						
						if updatingPin == True and enteringNewPin == False:
							if len(currentPin) == 0:
								success = delete_user(currentCard)
								if success == True:
									print "User with card " + currentCard + " was deleted from the database."
									
								else:
									print "User could not be deleted, probably because the user was deleted between the swipe of the card and the delete command"
									
								print "Going back into card entry mode...\n"
								waitingForCard = True
								updatingPin = False
								enteringNewPin = False
								currentPin = ""
								currentCard = ""
								currentUser = None
									
							else:
								if currentUser[2] == currentPin:
									print "Old pin correct! Enter new pin."
									enteringNewPin = True
									oldUserPin = currentPin
									currentPin = ""
									
								else:
									print "Old pin invalid, try again or hit # to go back to card entry mode.\n"
									currentPin = ""
										
						else:
							
							if len(currentPin) >= PIN_MIN_LENGTH:
								
								if enteringNewPin == True:
									success = update_user_pin(currentCard,oldUserPin,currentPin)
									if success == True:
										print "Updated User for card " + currentCard + " with new pin " + currentPin + " in the DB"
									else:
										print "User not updated, this indicates that the user was deleted between swiping the card and updating the user pin."
										
									print "Going back into card entry mode...\n"
									waitingForCard = True
									updatingPin = False
									enteringNewPin = False
									currentPin = ""
									currentCard = ""
									currentUser = None
									
								else:
									success = create_user(currentCard, currentPin)
									
									if success == True:
										print "Created User for card " + currentCard + " with pin " + currentPin + " in the DB"
									else:
										print "User not created, this indicates that this card already exists and was created in the time between swiping the card and entering the user pin."
									
									print "Going back into card entry mode...\n"
									waitingForCard = True
									currentPin = ""
									currentCard = ""
									currentUser = None
									#this shouldn't need to be here, but what the hell why not
									updatingPin = False
									enteringNewPin = False
							else:
								print "Pin too short, pin must be at least "+str(PIN_MIN_LENGTH)+" characters."
								print "Currently entered pin " + currentPin
						
						
					elif serialData[1] == "11":
						print "pin entry canceled, going to card entry mode..."
						currentCard = ""
						currentPin = ""
						updatingPin = False
						enteringNewPin = False
						waitingForCard = True
					else:
						currentPin += serialData[1]
						print "Currently entered pin " + currentPin
		else:
			val = val.replace("\r","")
			val = val.replace("\n","")
			#if val != HEARTBEAT:
			#	print "WHERE THE @#$&#*@ IS THE MAGLOCK SYSTEM!?!"
						
			
			
	
def serial_read_loop(ser):

	#All we do here is constantly read the serial line for data

	waitingForCard = True

	currentPin = ""

	controlCardPresent = False
	pinTimeout = datetime.datetime.min
	pinExpired = False
	currentUser = None

	while True:
		
		pinExpired = (datetime.datetime.now() - pinTimeout) > datetime.timedelta(seconds=PIN_ENTRY_TIMEOUT)
				#this means we've been waiting for a pin longer than the timeout value
		if pinExpired == True and waitingForCard == False:
			print "Pin entry timed out, going back into card read mode..."
			ser.write("RESET")
			currentUser = None
			waitingForCard = True
			
		val = ser.readline()
		
		serialData = process_serial(val)
		
		
		if serialData != False:

			if waitingForCard == True:
				if serialData[0] == "26CARD":
					
					if serialData[1] == CONTROL_CARD:
						print "the master... he approaches!"
						pinTimeout = datetime.datetime.now()
						controlCardPresent = True
						waitingForCard = False
					else:
						#check here to see if the card is in the DB
						currentUser = lookup_user(serialData[1])
						
						
						if currentUser == []:
							print "Card not in DB... try again"
							ser.write("RESET")
							currentUser = None
						else:
							currentUser = currentUser[0]
							waitingForCard = False
							pinTimeout = datetime.datetime.now()
							print "Enter the pincode... "
					
			else:
				if serialData[0] == "KEY":
					
					if serialData[1] == "10":
						
						if controlCardPresent == True:
							if currentPin == CONTROL_PIN:
								print "THE MASTER, HE IS HERE"
								currentPin = ""
								controlCardPresent = False
								waitingForCard = True
								currentUser = None
								control_read_loop(ser)
							else:
								print "Pin is incorrect. Going back into card entry mode...\n"
								
							
							currentPin = ""
							controlCardPresent = False
							waitingForCard = True
							currentUser = None
							
						else:
							if currentPin == currentUser[2]:
								print "Pin correct! Disengaging maglock..."
								ser.write("OPEN")
								time.sleep(2.5)
								print "Maglock re-engaged! Going back into card entry mode...\n"
								
							else:
								print "Pin is incorrect. Going back into card entry mode...\n"
								
							waitingForCard = True
							currentPin = ""
							currentUser = None
							
							#print get_all_users()
							#do DB query checks here
						
							
					elif serialData[1] == "11":
						print "Pin entry canceled, going back to card mode...\n"
						controlCardPresent = False
						waitingForCard = True
					else:
						pinTimeout = datetime.datetime.now()
						currentPin += serialData[1]
					#check here to see if the pin matches the one associated with the card


		else:
			val = val.replace("\r","")
			val = val.replace("\n","")
			#if val != HEARTBEAT:
			#	print "WHERE THE @#$&#*@ IS THE MAGLOCK SYSTEM!?!"
				
				
			


init_maglockdb()
#serial connection var
ser = None

ser = init_serial('/dev/ttyACM0')

serial_read_loop(ser)


