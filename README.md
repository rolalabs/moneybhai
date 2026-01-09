# moneybhai
keeps a track of personal finance


# Gmail Auth Flow
STEP 1: Android → Google Sign-In
        ↓
        ID TOKEN (identity only)

STEP 2: Android → Backend
        ↓
        Send ID token

STEP 3: Backend verifies ID token
        ↓
        "Yes, this user is saswat@gmail.com"

STEP 4: Backend asks user for Gmail permission (ONCE)
        ↓
        OAuth consent screen

STEP 5: Google → Backend
        ↓
        Gmail access + refresh tokens

STEP 6: Backend stores refresh token
        ↓
        Backend can fetch emails forever

STEP 7: Android just calls your backend
