
import bcrypt

 
 
class Hash:
    
    def hashing(password):
        """
        Hashes the given password using a predefined password context.

        Args:
            password (str): The plaintext password to be hashed.

        Returns:
            str: The hashed version of the password.
        """
        return bcrypt.hashpw(password.encode(), salt=bcrypt.gensalt()) # encrypt the password
    
        
    def verify(plain_password, hashed_password):
        """
        Verifies whether the provided plain text password matches the hashed password.

        Args:
            plain_password (str): The plain text password to verify.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the plain password matches the hashed password, False otherwise.
        """
        return bcrypt.checkpw(plain_password.encode(), hashed_password) # decrypt the password