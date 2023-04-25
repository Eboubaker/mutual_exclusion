TP Distributed Systems: [Ricart & Agrawala Mutual Exclusion Algorithm](https://elearning.univ-eloued.dz/pluginfile.php/14504/mod_resource/content/1/SD2_Cours.pdf) or [here](https://docplayer.fr/7218114-Algorithmique-du-controle-reparti.html) [page 17|13]

> if you want to use a database then add the `use_db` argument when running and modify database credentials in main.py and create required mysql table `counter(counter int)` and `usage_history(machine_port varchar, data text, time timestamp)`
```
pip install -r requirements.txt
python main.py
```
run 3 or more instances of main.py, with required argument `our_port` and `processes_ports` (comma seperated) to use a database as a resource instead of a file add `use_db` argument.

each node must know the other processes (using `processes_ports` arguemnt)

instance 1
```
python main.py our_port=8001 processes_ports=8002,8003
```
instance 2
```
python main.py our_port=8002 processes_ports=8001,8003
```
instance 3
```
python main.py our_port=8003 processes_ports=8002,8001
```

input something in any instance to write to the database/file.
- while an instance is writing no other instance is allowed to use the resource.  
- if an instance wants to write it must request from other instances the permission.   
- if an instance got a request to write from other process it will give the permission if it is currently not using the resource. if it is using the resource it will put the requester's id(port) into a waiting list. after it's done using the resource it will send the permission to all waiting nodes.
- a process may only start using the resource when it has recivied a permission-reply from all other known processes
- if a process got a request to write from another process and it also wants to use the resource at the same time, the process should give it's permission to the other process depending on the request time, or put it in the waiting list if otherwise.