TP Distributed Systems: Lann [Token ring](https://www.cs.colostate.edu/~cs551/CourseNotes/Synchronization/RingElectExample.html) algorithm

modify database credentials in main.py and create required mysql table `counter(counter int)` and `usage_history(machine_port varchar, data text, time timestamp)`
```
pip install -r requirements.txt
python main.py
```
run 3 or more instances of main.py, and link each one to form a cycle

instance 1 (set environment variable to start the cycle)
```
set RING_START=1
python main.py
our_port=6777
successor_port=6888
```
instance 2
```
python main.py
our_port=6888
successor_port=6999
```
instance 3
```
python main.py
our_port=6999
successor_port=6777
```
input something in any instance to write to the database.
- while an instance is writing no other instance is allowed to use the resource untill the cycling token has reached it.  
- if an instance wants to write but does not have the token of the resource yet, it should wait until it's predecessor sends it the token for the resource.   
- after an instance has acquired the token it may start using the resource right away(enter critical code) then send the token to it's successor, if it doesn't need the resource it should send the token to it's successor right away the token must keep cycling.
