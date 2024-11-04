from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import select, Session
from pydantic import BaseModel

from app.db import get_db
from app.models import Location, Organisation, CreateOrganisation

router = APIRouter()

@router.post("/create", response_model=Organisation)
def create_organisation(create_organisation: CreateOrganisation, session: Session = Depends(get_db)) -> Organisation:
    """Create an organisation."""
    organisation = Organisation(name=create_organisation.name)
    session.add(organisation)
    session.commit()
    session.refresh(organisation)
    return organisation


@router.get("/", response_model=list[Organisation])
def get_organisations(session: Session = Depends(get_db)) -> list[Organisation]:
    """
    Get all organisations.
    """
    organisations = session.exec(select(Organisation)).all()
    return organisations



@router.get("/{organisation_id}", response_model=Organisation)
def get_organisation(organisation_id: int, session: Session = Depends(get_db)) -> Organisation:
    """
    Get an organisation by id.
    """
    organisation = session.get(Organisation, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation


@router.post("/create/locations")
def create_location():
    raise NotImplementedError

class LocationResponse(BaseModel):
    location_name: str
    location_longitude: float
    location_latitude: float

@router.get("/{organisation_id}/locations")
def get_organisation_locations(organisation_id: int, session: Session = Depends(get_db)):
    """
    get all locations for a given organisation id.
    """
    organisation = session.get(Organisation, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organisation not found")

    locations = session.exec(select(Location).where(Location.organisation_id == organisation_id)).all()
    
    if not locations:
        return []

    return [
        LocationResponse(
            location_name=location.location_name,
            location_longitude=location.longitude,
            location_latitude=location.latitude,
        )
        for location in locations
    ]

@router.get("/create/location")
async def create_location_get(session: Session = Depends(get_db)):
    """
    endpoint from the first task to create locations
    """
    new_location = Location(location_name="Default Name", longitude=0.0, latitude=0.0, organisation_id=1)
    session.add(new_location)
    session.commit()
    session.refresh(new_location)
    return {"message": "Location created", "location": new_location}
