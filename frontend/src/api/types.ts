export interface ApiResp<T = any> {
  code: number
  data: T
  msg: string
}

export interface CategoryNode {
  id: number
  space_id: number
  parent_id: number | null
  name: string
  sort_order: number
  photo_count: number
  created_at: string
  children: CategoryNode[]
}

export interface Photo {
  id: number
  category_id: number
  original_name: string
  file_size: number
  upload_time: string
  thumbnail_url: string | null
  image_url: string
  avg_score: number
  rating_count: number
  comment_count: number
  my_score: number | null
  my_favorite: boolean
}

export interface Comment {
  id: number
  photo_id: number
  author: string
  is_leader: boolean
  is_pinned: boolean
  content: string
  likes_count: number
  liked_by_me: boolean
  can_edit: boolean
  created_at: string
  updated_at: string
}

export interface PhotoDetail extends Photo {
  comments: Comment[]
}

export interface StatsRow {
  photo_id: number
  original_name: string
  category_path: string
  thumbnail_url: string | null
  image_url: string
  avg_score: number
  rating_count: number
  comment_count: number
  total_likes: number
  total_favorites: number
}

export type SortKey = 'score' | 'time' | 'count'
