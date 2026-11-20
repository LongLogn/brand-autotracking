import type { ApiBrand, ApiTrackingConfig, createApiClient } from './api';

type BrandApi = Pick<ReturnType<typeof createApiClient>, 'createBrand' | 'setTracking'>;

/** Kết quả tách biệt vì API tạo nhãn hàng và lưu cấu hình không phải một giao dịch. */
export type CreateBrandResult =
  | { status: 'complete'; brand: ApiBrand; tracking: ApiTrackingConfig }
  | { status: 'tracking-failed'; brand: ApiBrand; error: unknown };

export async function createBrandWithTracking(
  api: BrandApi,
  name: string,
  config: ApiTrackingConfig,
  signal?: AbortSignal,
  idempotencyKey?: string,
): Promise<CreateBrandResult> {
  // Lỗi bước tạo được chuyển tiếp: chưa có ID để biết có thể tiếp tục hay không.
  const brand = await api.createBrand(name, signal, idempotencyKey);
  try {
    const tracking = await api.setTracking(brand.id, config, signal);
    return { status: 'complete', brand, tracking };
  } catch (error) {
    return { status: 'tracking-failed', brand, error };
  }
}

/** Thử lại riêng bước cấu hình, dùng ID đã trả về từ bước tạo. */
export function retryBrandTracking(api: BrandApi, brand: ApiBrand, config: ApiTrackingConfig, signal?: AbortSignal) {
  return api.setTracking(brand.id, config, signal);
}
