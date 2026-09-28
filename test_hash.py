import bcrypt

hashed_password = "$2b$12$j0/rYE65FTC7QYHV/lISPOZ0EKKQ4MMwrblYAEDE8hwI14OWRuKh."
plain_password = "userrubal"

print("Starts with $2?", hashed_password.startswith("$2"))
try:
    is_valid = bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    print("Is Valid:", is_valid)
except Exception as e:
    print("Error:", str(e))
