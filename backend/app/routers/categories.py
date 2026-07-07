from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_actor, require_leader, Actor
from ..models import Category, Photo, Space
from ..response import ApiError, ok
from ..schemas import CategoryCreate, CategoryOut, CategoryReorder, CategoryUpdate

router = APIRouter(prefix="/api/spaces/{space_id}/categories", tags=["categories"])


def _photo_counts(db: Session, space_id: int) -> dict[int, int]:
    rows = (
        db.query(Photo.category_id, func.count(Photo.id))
        .join(Category, Category.id == Photo.category_id)
        .filter(Category.space_id == space_id)
        .group_by(Photo.category_id)
        .all()
    )
    return {cid: int(cnt) for cid, cnt in rows}


def _build_tree(cats: list[Category], counts: dict[int, int]) -> list[dict]:
    nodes: dict[int, dict] = {}
    for c in cats:
        nodes[c.id] = CategoryOut(
            id=c.id,
            space_id=c.space_id,
            parent_id=c.parent_id,
            name=c.name,
            sort_order=c.sort_order,
            photo_count=counts.get(c.id, 0),
            created_at=c.created_at,
            children=[],
        ).model_dump()

    roots: list[dict] = []
    for c in cats:
        node = nodes[c.id]
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def sort_rec(items: list[dict]):
        items.sort(key=lambda x: (x["sort_order"], -x["id"]))
        for it in items:
            sort_rec(it["children"])

    sort_rec(roots)
    return roots


@router.get("")
def list_categories(space_id: int, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    cats = (
        db.query(Category)
        .filter(Category.space_id == space_id)
        .order_by(Category.sort_order.asc(), Category.created_at.desc())
        .all()
    )
    counts = _photo_counts(db, space_id)
    return ok(_build_tree(cats, counts))


@router.post("")
def create_category(
    space_id: int,
    payload: CategoryCreate,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    if payload.parent_id is not None:
        parent = db.get(Category, payload.parent_id)
        if not parent or parent.space_id != space_id:
            raise ApiError("父分类不存在", code=404, status_code=404)

    # New categories sort first (created desc default): use smallest sort_order.
    min_order = (
        db.query(func.min(Category.sort_order))
        .filter(Category.space_id == space_id, Category.parent_id == payload.parent_id)
        .scalar()
    )
    sort_order = (min_order - 1) if min_order is not None else 0

    cat = Category(
        space_id=space_id,
        parent_id=payload.parent_id,
        name=payload.name.strip(),
        sort_order=sort_order,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return ok({"id": cat.id, "name": cat.name, "parent_id": cat.parent_id})


@router.put("/{category_id}")
def update_category(
    space_id: int,
    category_id: int,
    payload: CategoryUpdate,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, category_id)
    if not cat or cat.space_id != space_id:
        raise ApiError("分类不存在", code=404, status_code=404)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise ApiError("分类名称不能为空")
        cat.name = name

    if payload.parent_id is not None and payload.parent_id != cat.parent_id:
        if payload.parent_id == category_id:
            raise ApiError("不能将分类移动到自身下")
        parent = db.get(Category, payload.parent_id)
        if not parent or parent.space_id != space_id:
            raise ApiError("目标父分类不存在", code=404, status_code=404)
        # prevent cycles
        cur = parent
        guard = 0
        while cur and guard < 50:
            if cur.id == category_id:
                raise ApiError("不能移动到自己的子分类下")
            cur = db.get(Category, cur.parent_id) if cur.parent_id else None
            guard += 1
        cat.parent_id = payload.parent_id

    db.commit()
    return ok({"id": cat.id, "name": cat.name, "parent_id": cat.parent_id})


@router.put("/reorder/batch")
def reorder_categories(
    space_id: int,
    payload: CategoryReorder,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    id_map = {
        c.id: c
        for c in db.query(Category).filter(Category.space_id == space_id).all()
    }
    for item in payload.items:
        cat = id_map.get(item.id)
        if cat:
            cat.sort_order = item.sort_order
    db.commit()
    return ok({"updated": len(payload.items)})


@router.delete("/{category_id}")
def delete_category(
    space_id: int,
    category_id: int,
    space: Space = Depends(require_leader),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, category_id)
    if not cat or cat.space_id != space_id:
        raise ApiError("分类不存在", code=404, status_code=404)

    photo_count = db.query(func.count(Photo.id)).filter(Photo.category_id == category_id).scalar()
    if photo_count and photo_count > 0:
        raise ApiError("非空分类不可删除，请先移除图片")

    child_count = (
        db.query(func.count(Category.id)).filter(Category.parent_id == category_id).scalar()
    )
    if child_count and child_count > 0:
        raise ApiError("请先删除子分类")

    db.delete(cat)
    db.commit()
    return ok({"deleted": category_id})
