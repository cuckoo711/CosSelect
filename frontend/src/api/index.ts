import { request } from './client'
import type { CategoryNode, Comment, Photo, PhotoDetail, SortKey, StatsRow } from './types'

// ---------- Spaces ----------
export const createSpace = () =>
  request<{ space_id: string; invite_code: string; manage_key: string; expire_time: string }>({
    url: '/api/spaces',
    method: 'post',
  })

export const regenerateCode = (spaceId: string) =>
  request<{ space_id: string; invite_code: string; expire_time: string }>({
    url: `/api/spaces/${spaceId}/regenerate-code`,
    method: 'post',
  })

export const verifyCodeGlobal = (code: string) =>
  request<{ valid: boolean; space_id: string | null }>({
    url: '/api/spaces/verify-code',
    method: 'post',
    data: { code },
  })

export const getSpaceInfo = (spaceId: string) =>
  request<{
    space_id: string
    invite_code: string
    expire_time: string
    expired: boolean
    require_approval: boolean
    last_access_at: string | null
    inactive_notice_days: number
    inactive_destroy_days: number
  }>({
    url: `/api/spaces/${spaceId}/info`,
  })

// ---------- Participants ----------
export const joinSpace = (spaceId: string, nickname: string) =>
  request<{
    participant_id: number
    nickname: string
    token: string
    is_new: boolean
    status: string
  }>({
    url: `/api/spaces/${spaceId}/participants`,
    method: 'post',
    data: { nickname },
  })

export const getMyStatus = (spaceId: string, nickname: string) =>
  request<{ status: string; participant_id?: number }>({
    url: `/api/spaces/${spaceId}/participants/me/status`,
    params: { nickname },
  }, true)

// ---------- Approvals (leader) ----------
export const listPendingParticipants = (
  spaceId: string,
  status: 'pending' | 'approved' | 'rejected' | 'all' = 'pending',
) =>
  request<{ participant_id: number; nickname: string; status: string; join_time: string }[]>({
    url: `/api/spaces/${spaceId}/participants-list`,
    params: { status },
  })

export const approveParticipant = (spaceId: string, participantId: number) =>
  request({ url: `/api/spaces/${spaceId}/participants/${participantId}/approve`, method: 'post' })

export const rejectParticipant = (spaceId: string, participantId: number) =>
  request({ url: `/api/spaces/${spaceId}/participants/${participantId}/reject`, method: 'post' })

export const setApprovalSetting = (spaceId: string, requireApproval: boolean) =>
  request<{ require_approval: boolean }>({
    url: `/api/spaces/${spaceId}/settings/approval`,
    method: 'put',
    data: { require_approval: requireApproval },
  })

// ---------- Categories ----------
export const listCategories = (spaceId: string) =>
  request<CategoryNode[]>({ url: `/api/spaces/${spaceId}/categories` })

export const createCategory = (spaceId: string, name: string, parentId: number | null) =>
  request({
    url: `/api/spaces/${spaceId}/categories`,
    method: 'post',
    data: { name, parent_id: parentId },
  })

export const updateCategory = (
  spaceId: string,
  categoryId: number,
  payload: { name?: string; parent_id?: number | null },
) =>
  request({
    url: `/api/spaces/${spaceId}/categories/${categoryId}`,
    method: 'put',
    data: payload,
  })

export const reorderCategories = (
  spaceId: string,
  items: { id: number; sort_order: number }[],
) =>
  request({
    url: `/api/spaces/${spaceId}/categories/reorder/batch`,
    method: 'put',
    data: { items },
  })

export const deleteCategory = (spaceId: string, categoryId: number) =>
  request({ url: `/api/spaces/${spaceId}/categories/${categoryId}`, method: 'delete' })

// ---------- Photos ----------
export const listPhotos = (spaceId: string, categoryId: number, sort: SortKey) =>
  request<Photo[]>({
    url: `/api/spaces/${spaceId}/photos`,
    params: { category_id: categoryId, sort },
  })

export const getPhotoDetail = (spaceId: string, photoId: number) =>
  request<PhotoDetail>({ url: `/api/spaces/${spaceId}/photos/${photoId}` })

export const deletePhoto = (spaceId: string, photoId: number) =>
  request({ url: `/api/spaces/${spaceId}/photos/${photoId}`, method: 'delete' })

export function uploadPhotos(
  spaceId: string,
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
export const submitRating = (spaceId: string, photoId: number, score: number) =>
  request<{ photo_id: number; avg_score: number; rating_count: number; my_score: number }>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/ratings`,
    method: 'post',
    data: { score },
  })

// ---------- Comments ----------
export const listComments = (spaceId: string, photoId: number) =>
  request<Comment[]>({ url: `/api/spaces/${spaceId}/photos/${photoId}/comments` })

export const createComment = (spaceId: string, photoId: number, content: string) =>
  request<Comment>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/comments`,
    method: 'post',
    data: { content },
  })

export const updateComment = (spaceId: string, commentId: number, content: string) =>
  request<Comment>({
    url: `/api/spaces/${spaceId}/comments/${commentId}`,
    method: 'put',
    data: { content },
  })

export const deleteComment = (spaceId: string, commentId: number) =>
  request({ url: `/api/spaces/${spaceId}/comments/${commentId}`, method: 'delete' })

export const toggleLike = (spaceId: string, commentId: number) =>
  request<{ comment_id: number; likes_count: number; liked_by_me: boolean }>({
    url: `/api/spaces/${spaceId}/comments/${commentId}/like`,
    method: 'post',
  })

// ---------- Favorites ----------
export const toggleFavorite = (spaceId: string, photoId: number) =>
  request<{ photo_id: number; favorite: boolean }>({
    url: `/api/spaces/${spaceId}/photos/${photoId}/favorite`,
    method: 'post',
  })

// ---------- Stats ----------
export const getStats = (spaceId: string) =>
  request<StatsRow[]>({ url: `/api/spaces/${spaceId}/stats` })

export const exportCsvUrl = (spaceId: string) => `/api/spaces/${spaceId}/export`
