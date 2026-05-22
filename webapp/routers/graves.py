"""Qabrlar — ro'yxat, qo'shish, va viloyat/tuman/qabriston API'lari."""
from fastapi import APIRouter, Depends, Form, Request
from starlette.responses import JSONResponse, RedirectResponse

from bot.database.models import RELATIONSHIP_CHOICES
from bot.database.queries import (
    add_grave,
    get_cemeteries_by_district,
    get_cemetery_by_id,
    get_district_by_id,
    get_districts_by_region,
    get_region_by_id,
    get_regions,
    list_user_graves,
)
from webapp.deps import get_current_user, get_db, render, set_flash

router = APIRouter()


@router.get("/graves")
async def graves_list(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    graves = await list_user_graves(session, user.id)
    return render(request, "graves.html", {"user": user, "graves": graves})


@router.get("/graves/add")
async def grave_add_form(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    regions = await get_regions(session)
    lang = user.language or "uz"
    return render(request, "grave_add.html", {
        "user": user,
        "regions": [{"id": r.id, "name": r.get_name(lang)} for r in regions],
        "relationships": RELATIONSHIP_CHOICES,
    })


@router.post("/graves/add")
async def grave_add_submit(
    request: Request,
    region_id: str = Form(""),
    district_id: str = Form(""),
    cemetery_id: str = Form(""),
    deceased_full_name: str = Form(""),
    birth_year: str = Form(""),
    death_year: str = Form(""),
    relationship: str = Form("Other"),
    dates_precise: str = Form("1"),
    user=Depends(get_current_user),
    session=Depends(get_db),
):
    if not user:
        return RedirectResponse("/login", status_code=303)
    deceased = deceased_full_name.strip()
    errors: list[str] = []
    if len(deceased) < 2:
        errors.append("Marhumning ism-familiyasini kiriting.")
    region = await get_region_by_id(session, int(region_id)) if region_id.isdigit() else None
    district = await get_district_by_id(session, int(district_id)) if district_id.isdigit() else None
    cemetery = await get_cemetery_by_id(session, int(cemetery_id)) if cemetery_id.isdigit() else None
    if not (region and district and cemetery):
        errors.append("Viloyat, tuman va qabristonni tanlang.")
    if errors:
        regions = await get_regions(session)
        lang = user.language or "uz"
        return render(request, "grave_add.html", {
            "user": user, "errors": errors,
            "regions": [{"id": r.id, "name": r.get_name(lang)} for r in regions],
            "relationships": RELATIONSHIP_CHOICES,
        })

    def _year(value: str) -> int | None:
        value = (value or "").strip()
        return int(value) if value.isdigit() and 1800 <= int(value) <= 2100 else None

    lang = user.language or "uz"
    is_approx = dates_precise != "1"
    await add_grave(
        session, user.id,
        region=region.get_name(lang),
        district=district.get_name(lang),
        cemetery=cemetery.name,
        deceased_full_name=deceased,
        birth_year=_year(birth_year),
        birth_approximate=is_approx,
        death_year=_year(death_year),
        death_approximate=is_approx,
        relationship_status=relationship,
    )
    set_flash(request, "Qabr ma'lumoti qo'shildi.")
    return RedirectResponse("/graves", status_code=303)


@router.get("/api/districts")
async def api_districts(region_id: int, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return JSONResponse([], status_code=401)
    lang = user.language or "uz"
    districts = await get_districts_by_region(session, region_id)
    return JSONResponse([{"id": d.id, "name": d.get_name(lang)} for d in districts])


@router.get("/api/cemeteries")
async def api_cemeteries(district_id: int, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return JSONResponse([], status_code=401)
    cemeteries = await get_cemeteries_by_district(session, district_id)
    return JSONResponse([{"id": c.id, "name": c.name} for c in cemeteries])
