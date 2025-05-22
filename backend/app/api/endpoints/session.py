from fastapi import APIRouter

router = APIRouter()

@router.post("/logout")
def logout():
    """
    With JWT tokens, logout is handled client-side by removing the token.
    This endpoint exists for consistency and future extension.
    """
    return {"status": "success", "message": "Logout successful"}