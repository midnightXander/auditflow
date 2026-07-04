import redis

# Replace with your VM's IP address
vm_ip = "192.168.56.101"   
port = 6379              # Default Redis port
password = None          # Set if you configured requirepass in redis.conf

# Create connection
r = redis.Redis(host=vm_ip, port=port, password=password, decode_responses=True)

# Test connection
try:
    pong = r.ping()
    if pong:
        print("Connected to Redis!")
except Exception as e:
    print("Connection failed:", e)
