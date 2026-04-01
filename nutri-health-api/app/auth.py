"""
Authentication utilities for NutriHealth API
Handles JWT token creation, validation, and user authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
import logging

logger = logging.getLogger(__name__)

# Configuration from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# Hardcoded credentials for demo purposes
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme with token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash for a password.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The bcrypt hashed password
    """
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate user against hardcoded credentials.
    
    For this demo application, we use hardcoded username and password.
    In production, this would check against a database.
    
    Args:
        username: The username to authenticate
        password: The password to verify
        
    Returns:
        True if credentials are valid, False otherwise
    """
    # Check username
    if username != DEMO_USERNAME:
        logger.warning(f"Authentication failed: invalid username '{username}'")
        return False
    
    # For demo, directly compare password
    # In production, you would compare against hashed password from database
    if password != DEMO_PASSWORD:
        logger.warning(f"Authentication failed: invalid password for user '{username}'")
        return False
    
    logger.info(f"User '{username}' authenticated successfully")
    return True


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing claims to encode in the token
              Should include 'sub' (subject) with the username
              
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Add expiration time
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    
    # Encode JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    logger.info(f"Created access token for user '{data.get('sub')}' expiring at {expire}")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: The JWT token string to decode
        
    Returns:
        Dictionary containing the token claims if valid, None otherwise
    """
    try:
        # Decode and validate token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract username from subject claim
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token validation failed: missing 'sub' claim")
            return None
        
        return {"username": username}
    
    except JWTError as e:
        logger.warning(f"Token validation failed: {str(e)}")
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to validate bearer token and get current user.
    
    This function is used as a FastAPI dependency to protect endpoints.
    It validates the JWT token and returns the user information.
    
    Args:
        token: The bearer token from the Authorization header
        
    Returns:
        Dictionary containing user information
        
    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    print('Getting current user', token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode and validate token
    token_data = decode_access_token(token)
    print('token data', token_data)
    if token_data is None:
        raise credentials_exception
    
    logger.info(f"Token validated successfully for user '{token_data['username']}'")
    return token_data
