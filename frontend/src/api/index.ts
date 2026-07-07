import { request } from './client'
import type { CategoryNode, Comment, Photo, PhotoDetail, SortKey, StatsRow } from './types'

// ---------- Spaces ----------
export const createSpace = () =>
  request<{ space_id: number; invite_code: string; manage_key: string; expire_time: string }>({
    url: '/api/spaces',
    method: 'post',
  })

export const regenerateCode = (spaceId: number) =>
  request<{ space_id: number; invite_code: string; expire_time: string }>({
    url: `/api/spaces/${spaceId}/regenerate-code`,
    method: 'post',
  })

export const verifyCodeGlobal = (code: string) =>
  request<{ valid: boolean; space_id: number | null }>({
    url: '/api/spaces/verify-code',
    method: 'post',
    data: { code },
  })

export const getSpaceInfo = (spaceId: number) =>
  request<{ space_id: number; invite_code: string; expire_time: string; expired: boolean }>({
    url: `/api/spaces/${spaceId}/info`,
  })

// ---------- Participants ----------
export const joinSpace = (spaceId: number, nickname: string) =>
  request<{ participant_id: number; nickname: string; token: string; is_new: boolean }>({
    url: `/api/spaces/${spaceId}/participants`,
    method: 'post',
    data: { nickname },
  })

// ---------- Categories ----------
export const listCategories = (spaceId: number) =>
  request<CategoryNode[]>({ url: `/api/spaces/${spaceId}/categories` })

export const createCategory = (spaceId: number, name: string, parentId: number | null) =>
  request({
    url: `/api/spaces/${spaceId}/categories`,
    method: 'post',
    data: { name, parent_id: parentId },
  })

export const updateCategory = (
  spaceId: number,
  categoryId: number,
  payload: { name?: string; parent_id?: number | null },
) =>
  request({
    url: `/api/spaces/${spaceId}/categories/${categoryId}`,
    method: 'put',
    data: payload,
  })

export const reorderCategories = (
  spaceId: number,
  items: { id: number; sort_order: number }[],
) =>
  request({
    url: `/api/spaces/${spaceId}/categories/reorder/batch`,
    method: 'put',
    data: { items },
  })

export const deleteCategory = (spaceId: number, categoryId: number) =>
  request({ url: `/api/spaces/${spaceId}/categories/${categoryId}`, method: 'delete' })

// ---------- Photos ----------
export const listPhotos = (spaceId: number, categoryId: number, sort: SortKey) =>
  request<Photo[]>({
    url: `/api/spaces/${spaceId}/photos`,
    params: { category_id: categoryId, sort },
  })

export const getPhotoDetail = (spaceId: number, photoId: number) =>
  request<PhotoDetail>({ url: `/api/spaces/${spaceId}/photos/${photoId}` })

export const deletePhoto = (spaceId: number, photoId: number) =>
  request({ url: `/api/spaces/${spaceId}/photos/${photoId}`, method: 'delete' })

export function uploadPhotos(
  spaceId: number,
  categoryId: number,
  files: File[],
  onProgress?: (pct: number) => void,
) {
  const form = new FormData()
  form.append('category_id', String(categoryId))
  files.forEach((f) => form.append('files', f))
  return request({
    url: `/api/spaces/${spaceId}/photos/upload`,
    method: 'post',
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
}

// ---------- Ratings ----------
export const submitRating = (spaceId: number, photoId: number, score: number) =>
  request<{ photo_id: number; avg_score: number; rating_count: number; my_score: number }>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/ratings`,
    method: 'post',
    data: { score },
  })

// ---------- Comments ----------
export const listComments = (spaceId: number, photoId: number) =>
  request<Comment[]>({ url: `/api/spaces/${spaceId}/photos/${photoId}/comments` })

export const createComment = (spaceId: number, photoId: number, content: string) =>
  request<Comment>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/comments`,
    method: 'post',
    data: { content },
  })

export const updateComment = (spaceId: number, commentId: number, content: string) =>
  request<Comment>({
    url: `/api/spaces/${spaceId}/comments/${commentId}`,
    method: 'put',
    data: { content },
  })

export const deleteComment = (spaceId: number, commentId: number) =>
  request({ url: `/api/spaces/${spaceId}/comments/${commentId}`, method: 'delete' })

export const toggleLike = (spaceId: number, commentId: number) =>
  request<{ comment_id: number; likes_count: number; liked_by_me: boolean }>({
    url: `/api/spaces/${spaceId}/comments/${commentId}/like`,
    method: 'post',
  })

// ---------- Favorites ----------
export const toggleFavorite = (spaceId: number, photoId: number) =>
  request<{ photo_id: number; favorite: boolean }>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/favorite`,
    method: 'post',
  })

// ---------- Stats ----------
export const getStats = (spaceId: number) =>
  request<StatsRow[]>({ url: `/api/spaces/${spaceId}/stats` })

export const exportCsvUrl = (spaceId: number) => `/api/spaces/${spaceId}/export`
