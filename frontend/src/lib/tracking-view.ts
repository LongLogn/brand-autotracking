import type { ApiAttempt, ApiComment, ApiPost, ApiRun, CommentFilters, createApiClient, Pagination } from './api';

type TrackingApi = Pick<ReturnType<typeof createApiClient>, 'getRun' | 'listRunPosts' | 'listRunComments'>;

/** Dữ liệu hiển thị giữ nguyên null khi backend chưa có số liệu. */
export function runView(run: ApiRun) {
  return {
    id: run.id,
    status: run.status,
    queuedAt: run.queued_at,
    startedAt: run.started_at,
    finishedAt: run.finished_at,
    errorCode: run.error_code,
  };
}

export function attemptView(attempt: ApiAttempt) {
  return {
    id: attempt.id,
    source: attempt.source,
    keyword: attempt.keyword,
    status: attempt.status,
    resultCount: attempt.result_count,
    errorCode: attempt.error_code,
    notice: attempt.notice ?? null,
  };
}

export function postView(post: ApiPost) {
  return {
    id: post.id,
    source: post.source,
    url: post.url,
    title: post.title,
    content: post.content,
    postedAt: post.posted_at,
    firstSeenAt: post.first_seen_at,
    likes: post.metrics?.likes ?? null,
    commentCount: post.metrics?.comment_count ?? null,
    maybeDuplicate: post.maybe_duplicate,
    sentiment: post.sentiment ?? 'unknown',
  };
}

export function commentView(comment: ApiComment) {
  return {
    id: comment.id,
    content: comment.content,
    postedAt: comment.posted_at,
    likes: comment.metrics?.likes ?? null,
    maybeDuplicate: comment.maybe_duplicate,
    sentiment: comment.sentiment ?? 'unknown',
  };
}

/** Tải chi tiết và một trang bài; không tự suy ra số lượng toàn bộ từ trang này. */
export async function loadRunPage(api: TrackingApi, brandId: string, runId: string, pagination?: Pagination, signal?: AbortSignal) {
  const [run, posts] = await Promise.all([
    api.getRun(brandId, runId, signal),
    api.listRunPosts(brandId, runId, signal, pagination),
  ]);
  return { run: runView(run), attempts: run.attempts.map(attemptView),
    collectionLimits: run.collection_limits, lookbackDays: run.lookback_days ?? undefined, posts: posts.map(postView) };
}

export async function loadRunComments(api: TrackingApi, brandId: string, runId: string, postId: string,
  pagination?: Pagination, signal?: AbortSignal, filters?: CommentFilters) {
  return (await api.listRunComments(brandId, runId, postId, signal, pagination, filters)).map(commentView);
}
