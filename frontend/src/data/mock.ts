// DỮ LIỆU MẪU (fixture) chỉ để dựng và trình diễn giao diện khi backend chưa có.
// Không phản ánh dữ liệu thật thu thập từ Firecrawl và không chứng minh nền tảng nào đã được hỗ trợ.

import type {
  Alert,
  AlertRule,
  AnalysisResult,
  Attempt,
  Brand,
  Platform,
  PlatformId,
  Post,
  Run,
  RunStatus,
} from './types';

export const PLATFORMS: Platform[] = [
  { id: 'reddit', name: 'Reddit', support: 'verified', note: 'Đã thử với từ khóa mẫu: lấy được bài, bình luận và điểm vote.' },
  { id: 'threads', name: 'Threads', support: 'experimental', note: 'Lấy được nội dung bài, thường không có số react và số bình luận.' },
  { id: 'facebook', name: 'Facebook', support: 'experimental', note: 'Nhiều trang yêu cầu đăng nhập, Firecrawl có thể không truy cập được.' },
  { id: 'tiktok', name: 'TikTok', support: 'unsupported', note: 'Chưa kiểm chứng được khả năng lấy nội dung, tạm chưa hỗ trợ.' },
];

export const platformName = (id: PlatformId) => PLATFORMS.find((p) => p.id === id)?.name ?? id;

const DAY = 86_400_000;
// 08:00 giờ Việt Nam ngày 14/11/2026
const TODAY_RUN = Date.UTC(2026, 10, 14, 1, 0);
const at = (daysAgo: number, minutes = 0) => new Date(TODAY_RUN - daysAgo * DAY + minutes * 60_000).toISOString();

export const NOW = at(0, 6 * 60 + 30); // 14:30 cùng ngày

export const SAMPLE_USER = { name: 'Nhóm demo', email: 'demo@vi-du.vn' };

export const INITIAL_BRANDS: Brand[] = [
  {
    id: 'ga-ran-abc',
    name: 'Gà rán ABC',
    description: 'Chuỗi gà rán, 12 chi nhánh tại Hà Nội',
    keywords: ['gà rán ABC', 'ga ran abc', 'abc chicken'],
    platforms: ['reddit', 'threads', 'facebook'],
    frequency: 'daily',
    runTime: '08:00',
    timezone: 'Asia/Ho_Chi_Minh',
    postLimit: 10,
    active: true,
    nextRunAt: at(-1),
  },
  {
    id: 'tra-sua-may',
    name: 'Trà sữa Mây',
    description: 'Thương hiệu trà sữa, bán online',
    keywords: ['trà sữa Mây', 'tra sua may'],
    platforms: ['reddit', 'threads'],
    frequency: 'weekly',
    runTime: '20:00',
    timezone: 'Asia/Ho_Chi_Minh',
    postLimit: 5,
    active: false,
    nextRunAt: null,
  },
  {
    id: 'bun-bo-co-ba',
    name: 'Bún bò Cô Ba',
    description: 'Quán bún bò, mới tạo',
    keywords: ['bún bò Cô Ba'],
    platforms: ['reddit'],
    frequency: 'daily',
    runTime: '07:00',
    timezone: 'Asia/Ho_Chi_Minh',
    postLimit: 10,
    active: true,
    nextRunAt: at(-1, -60),
  },
];

// 14 phiên hằng ngày của Gà rán ABC. Cửa sổ trước (13–7 ngày trước) có 10 bình luận tiêu cực,
// cửa sổ hiện tại (6–0 ngày trước) có 15, khớp ví dụ cảnh báo trong SRS mục 10.2.
const NEG_COMMENTS = [1, 2, 1, 2, 1, 2, 1, 2, 1, 3, 2, 2, 3, 2];
const NEG_POSTS = [0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 2, 1];
const POSTS = [14, 16, 13, 11, 15, 17, 14, 16, 15, 12, 18, 16, 19, 17];
const COMMENTS = [48, 52, 41, 37, 50, 55, 46, 53, 49, 40, 58, 51, 62, 57];
const FACEBOOK_FAILED_DAY = new Set([3, 10]);
const THREADS_EMPTY_DAY = new Set([5]);

const FB_ERROR = 'Firecrawl Scrape không truy cập được trang: nội dung yêu cầu đăng nhập.';

function buildAttempts(brand: Brand, dayIndex: number): Attempt[] {
  const attempts: Attempt[] = [];
  brand.platforms.forEach((platform, pi) => {
    brand.keywords.forEach((keyword, ki) => {
      if (platform === 'facebook' && FACEBOOK_FAILED_DAY.has(dayIndex)) {
        attempts.push({ platform, keyword, status: 'failed', results: 0, error: FB_ERROR });
        return;
      }
      const englishOnThreads = platform === 'threads' && keyword === 'abc chicken';
      if (englishOnThreads || (platform === 'threads' && THREADS_EMPTY_DAY.has(dayIndex))) {
        attempts.push({ platform, keyword, status: 'empty', results: 0 });
        return;
      }
      const results = Math.min(brand.postLimit, 2 + ((dayIndex * 3 + pi * 5 + ki * 7) % 7));
      attempts.push({ platform, keyword, status: 'success', results });
    });
  });
  return attempts;
}

function statusFrom(attempts: Attempt[]): RunStatus {
  const failed = attempts.filter((a) => a.status === 'failed').length;
  if (failed === 0) return 'success';
  if (failed === attempts.length) return 'failed';
  return 'partial';
}

function sentimentOf(total: number, negative: number, seed: number) {
  const unknown = 1 + (seed % 3);
  const positive = Math.round((total - negative - unknown) * (0.38 + (seed % 4) * 0.03));
  return { positive, neutral: total - negative - unknown - positive, negative, unknown };
}

const abc = INITIAL_BRANDS[0];
const abcRuns: Run[] = NEG_COMMENTS.map((_, i) => {
  const daysAgo = 13 - i;
  const attempts = buildAttempts(abc, i);
  return {
    id: `run-abc-${String(i + 1).padStart(2, '0')}`,
    brandId: abc.id,
    startedAt: at(daysAgo),
    finishedAt: at(daysAgo, 4 + (i % 5)),
    status: statusFrom(attempts),
    postLimit: abc.postLimit,
    attempts,
    posts: POSTS[i],
    comments: COMMENTS[i],
    negativePosts: NEG_POSTS[i],
    negativeComments: NEG_COMMENTS[i],
    sentiment: sentimentOf(POSTS[i] + COMMENTS[i], NEG_POSTS[i] + NEG_COMMENTS[i], i),
  };
});

const may = INITIAL_BRANDS[1];
const mayRuns: Run[] = [
  {
    id: 'run-may-01',
    brandId: may.id,
    startedAt: at(23, 12 * 60),
    finishedAt: at(23, 12 * 60 + 3),
    status: 'success',
    postLimit: 5,
    attempts: [
      { platform: 'reddit', keyword: 'trà sữa Mây', status: 'success', results: 3 },
      { platform: 'reddit', keyword: 'tra sua may', status: 'success', results: 2 },
      { platform: 'threads', keyword: 'trà sữa Mây', status: 'success', results: 5 },
      { platform: 'threads', keyword: 'tra sua may', status: 'empty', results: 0 },
    ],
    posts: 9,
    comments: 21,
    negativePosts: 1,
    negativeComments: 3,
    sentiment: { positive: 14, neutral: 11, negative: 4, unknown: 1 },
  },
  {
    id: 'run-may-02',
    brandId: may.id,
    startedAt: at(16, 12 * 60),
    finishedAt: at(16, 12 * 60 + 2),
    status: 'failed',
    postLimit: 5,
    attempts: [
      { platform: 'reddit', keyword: 'trà sữa Mây', status: 'failed', results: 0, error: 'Firecrawl trả về lỗi 429: vượt hạn mức gọi. Đã thử lại 3 lần.' },
      { platform: 'reddit', keyword: 'tra sua may', status: 'failed', results: 0, error: 'Firecrawl trả về lỗi 429: vượt hạn mức gọi. Đã thử lại 3 lần.' },
      { platform: 'threads', keyword: 'trà sữa Mây', status: 'failed', results: 0, error: 'Hết thời gian chờ sau 60 giây.' },
      { platform: 'threads', keyword: 'tra sua may', status: 'failed', results: 0, error: 'Hết thời gian chờ sau 60 giây.' },
    ],
    posts: 0,
    comments: 0,
    negativePosts: null,
    negativeComments: null,
    sentiment: null,
  },
  {
    id: 'run-may-03',
    brandId: may.id,
    startedAt: at(9, 12 * 60),
    finishedAt: null,
    status: 'skipped',
    postLimit: 5,
    attempts: [],
    posts: 0,
    comments: 0,
    negativePosts: null,
    negativeComments: null,
    sentiment: null,
    note: 'Nhãn hàng đã tạm dừng trước giờ chạy nên không tạo phiên mới.',
  },
];

export const INITIAL_RUNS: Run[] = [...abcRuns, ...mayRuns];

const runIds = (...days: number[]) => days.map((d) => `run-abc-${String(14 - d).padStart(2, '0')}`);

export const POSTS_FIXTURE: Post[] = [
  {
    id: 'p-101',
    brandId: abc.id,
    platform: 'reddit',
    url: 'https://www.reddit.com/r/VietNam/comments/vidu101',
    title: 'Gà rán ABC Cầu Giấy giờ trưa chờ lâu quá',
    text: 'Trưa nay mình đợi gần 35 phút mới có phần gà, quầy chỉ có một bạn nhân viên. Có ai bị giống vậy không?',
    postedAt: at(2, 5 * 60),
    reacts: 42,
    commentCount: 18,
    sentiment: 'negative',
    keywords: ['gà rán ABC', 'ga ran abc'],
    runIds: runIds(1, 0),
    firstSeenAt: at(1),
    comments: [
      { id: 'c-1011', text: 'Chi nhánh đó cuối tuần cũng vậy, mình chuyển sang đặt trước qua app.', postedAt: at(2, 6 * 60), reacts: 17, sentiment: 'negative' },
      { id: 'c-1012', text: 'Gà vẫn ngon nhưng chờ 30 phút thì không ổn, nên thêm người giờ cao điểm.', postedAt: at(2, 7 * 60), reacts: 23, sentiment: 'negative' },
      { id: 'c-1013', text: 'Hôm qua mình ăn ở Láng Hạ thì nhanh, chắc tùy chi nhánh.', postedAt: at(1, 2 * 60), reacts: 6, sentiment: 'neutral' },
    ],
  },
  {
    id: 'p-102',
    brandId: abc.id,
    platform: 'facebook',
    url: 'https://www.facebook.com/groups/reviewanuong/posts/vidu102',
    title: 'Review combo gà mật ong mới của ABC',
    text: 'Combo mới 89k, gà giòn, sốt mật ong không quá ngọt. Khoai hơi ít nhưng tổng thể đáng tiền.',
    postedAt: at(5, 3 * 60),
    reacts: 214,
    commentCount: 37,
    sentiment: 'positive',
    keywords: ['gà rán ABC'],
    runIds: runIds(5, 4, 2),
    firstSeenAt: at(5),
    comments: [
      { id: 'c-1021', text: 'Đồng ý, sốt mật ong là món ngon nhất của ABC từ trước tới giờ.', postedAt: at(5, 4 * 60), reacts: 58, sentiment: 'positive' },
      { id: 'c-1022', text: 'Giá này ổn so với mặt bằng chung.', postedAt: at(5, 5 * 60), reacts: 12, sentiment: 'positive' },
      { id: 'c-1023', text: 'Mua thử chưa ạ, combo có đổi được nước không?', postedAt: at(4, 1 * 60), reacts: null, sentiment: 'unknown' },
    ],
  },
  {
    id: 'p-103',
    brandId: abc.id,
    platform: 'threads',
    url: 'https://www.threads.net/@vidu/post/vidu103',
    title: 'Sốt cay của ABC có phải đã bớt cay?',
    text: 'Ai thấy sốt cay của ABC càng ngày càng ít cay không, ước gì có lựa chọn cay cấp độ.',
    postedAt: at(4, 9 * 60),
    reacts: null,
    commentCount: null,
    sentiment: 'neutral',
    keywords: ['gà rán ABC', 'ga ran abc'],
    runIds: runIds(4, 3),
    firstSeenAt: at(4),
    comments: [
      { id: 'c-1031', text: 'Có, đúng luôn. Mình phải xin thêm tương ớt.', postedAt: null, reacts: null, sentiment: 'negative' },
      { id: 'c-1032', text: 'Mình thì thấy vừa, cay quá trẻ con không ăn được.', postedAt: null, reacts: null, sentiment: 'neutral' },
    ],
  },
  {
    id: 'p-104',
    brandId: abc.id,
    platform: 'reddit',
    url: 'https://www.reddit.com/r/hanoi/comments/vidu104',
    title: 'Giá gà rán trên app giao đồ ăn chênh nhiều so với tại quán',
    text: 'Cùng combo nhưng đặt qua app đắt hơn khoảng 20%, chưa tính phí ship. ABC có kênh đặt riêng không?',
    postedAt: at(6, 2 * 60),
    reacts: 31,
    commentCount: 9,
    sentiment: 'negative',
    keywords: ['ga ran abc'],
    runIds: runIds(6),
    firstSeenAt: at(6),
    comments: [
      { id: 'c-1041', text: 'Có app riêng, có mã giảm giá cho đơn đầu.', postedAt: at(6, 3 * 60), reacts: 14, sentiment: 'neutral' },
      { id: 'c-1042', text: 'App riêng hay lỗi thanh toán, mình bỏ rồi.', postedAt: at(6, 4 * 60), reacts: 9, sentiment: 'negative' },
    ],
  },
  {
    id: 'p-105',
    brandId: abc.id,
    platform: 'facebook',
    url: 'https://www.facebook.com/abcfans/posts/vidu105',
    title: 'Nhân viên chi nhánh Hoàng Quốc Việt rất dễ thương',
    text: 'Con mình làm đổ nước, bạn nhân viên lau dọn và đổi cốc mới luôn, không phàn nàn gì.',
    postedAt: at(9, 4 * 60),
    reacts: 96,
    commentCount: 11,
    sentiment: 'positive',
    keywords: ['gà rán ABC'],
    runIds: runIds(9, 8),
    firstSeenAt: at(9),
    comments: [
      { id: 'c-1051', text: 'Chi nhánh này phục vụ tốt thật.', postedAt: at(9, 5 * 60), reacts: 8, sentiment: 'positive' },
    ],
  },
  {
    id: 'p-106',
    brandId: abc.id,
    platform: 'threads',
    url: 'https://www.threads.net/@vidu/post/vidu106',
    title: 'Mong ABC có món cay cho dân mê cay',
    text: 'Đi ăn với nhóm bạn, ai cũng hỏi có gà cay cấp độ không. Có thì chắc mình ghé thường xuyên hơn.',
    postedAt: at(11, 10 * 60),
    reacts: null,
    commentCount: null,
    sentiment: 'neutral',
    keywords: ['gà rán ABC'],
    runIds: runIds(11),
    firstSeenAt: at(11),
    comments: [
      { id: 'c-1061', text: 'Hóng món cay, các hãng khác có cả rồi.', postedAt: null, reacts: null, sentiment: 'neutral' },
    ],
  },
  {
    id: 'p-107',
    brandId: abc.id,
    platform: 'reddit',
    url: 'https://www.reddit.com/r/VietNam/comments/vidu107',
    title: 'ABC chicken ở Hà Nội có đáng thử không?',
    text: 'Mình mới chuyển ra Hà Nội, thấy ABC chicken nhiều chi nhánh. Có nên thử không mọi người?',
    postedAt: at(12, 1 * 60),
    reacts: 15,
    commentCount: 7,
    sentiment: 'neutral',
    keywords: ['abc chicken'],
    runIds: runIds(12),
    firstSeenAt: at(12),
    comments: [
      { id: 'c-1071', text: 'Nên thử combo mật ong, gà giòn lâu.', postedAt: at(12, 2 * 60), reacts: 11, sentiment: 'positive' },
      { id: 'c-1072', text: 'Ổn, nhưng tránh giờ trưa ở các chi nhánh văn phòng.', postedAt: at(12, 3 * 60), reacts: 11, sentiment: 'negative' },
    ],
  },
  {
    id: 'p-108',
    brandId: abc.id,
    platform: 'facebook',
    url: 'https://www.facebook.com/share/vidu108',
    title: 'Đơn giao về gà bị nguội',
    text: 'Đặt giao 2 phần, tới nơi gà nguội và mềm. Lần thứ hai bị như vậy rồi.',
    postedAt: null,
    reacts: 27,
    commentCount: null,
    sentiment: 'negative',
    keywords: ['gà rán ABC'],
    runIds: runIds(0),
    firstSeenAt: at(0),
    maybeDuplicate: true,
    comments: [],
  },
];

export const INITIAL_RULES: AlertRule[] = [
  {
    id: 'rule-1',
    brandId: abc.id,
    metric: 'negative-comments',
    windowDays: 7,
    growthPercent: 50,
    minCount: 5,
    absoluteThreshold: 10,
    enabled: true,
  },
  {
    id: 'rule-2',
    brandId: abc.id,
    metric: 'negative-posts',
    windowDays: 7,
    growthPercent: 100,
    minCount: 8,
    absoluteThreshold: null,
    enabled: true,
  },
];

export const INITIAL_ALERTS: Alert[] = [
  {
    id: 'alert-3',
    brandId: abc.id,
    ruleId: 'rule-1',
    createdAt: at(0, 9),
    kind: 'triggered',
    metric: 'negative-comments',
    windowLabel: '08/11 – 14/11 so với 01/11 – 07/11',
    previous: 10,
    current: 15,
    growthPercent: 50,
    threshold: 'Tăng từ 50% và tối thiểu 5 bình luận',
    reason: 'Bình luận tiêu cực tăng 50%, đạt ngưỡng của quy tắc.',
    read: false,
  },
  {
    id: 'alert-1',
    brandId: abc.id,
    ruleId: 'rule-1',
    createdAt: at(7, 9),
    kind: 'insufficient',
    metric: 'negative-comments',
    windowLabel: '01/11 – 07/11 so với 25/10 – 31/10',
    previous: null,
    current: 10,
    growthPercent: null,
    threshold: 'Tăng từ 50% và tối thiểu 5 bình luận',
    reason: 'Cửa sổ trước chưa có phiên nào vì nhãn hàng mới bắt đầu theo dõi. Không đủ cơ sở so sánh.',
    read: true,
  },
];

export const INITIAL_ANALYSES: AnalysisResult[] = [
  {
    id: 'an-1',
    brandId: abc.id,
    createdAt: at(0, 5 * 60),
    status: 'done',
    from: at(13),
    to: at(0),
    platforms: ['reddit', 'threads', 'facebook'],
    postCount: 8,
    commentCount: 15,
    dataAsOf: at(0, 9),
    gaps: [
      'Facebook thất bại ở 2 trong 14 phiên (04/11 và 11/11).',
      'Threads không cung cấp số react và số bình luận.',
      '1 bài Facebook không có định danh ổn định, có thể bị trùng.',
    ],
    findings: [
      {
        text: 'Thời gian chờ lâu giờ cao điểm là phàn nàn xuất hiện nhiều nhất, tập trung ở các chi nhánh khu văn phòng.',
        evidence: [
          { kind: 'post', id: 'p-101' },
          { kind: 'comment', id: 'c-1012' },
          { kind: 'comment', id: 'c-1072' },
        ],
      },
      {
        text: 'Nhiều người hỏi về món cay hoặc mức độ cay, kể cả trong bài không phàn nàn.',
        evidence: [
          { kind: 'post', id: 'p-103' },
          { kind: 'post', id: 'p-106' },
          { kind: 'comment', id: 'c-1031' },
          { kind: 'comment', id: 'c-1061' },
        ],
      },
      {
        text: 'Combo gà mật ong mới nhận phản hồi tích cực về vị và giá.',
        evidence: [
          { kind: 'post', id: 'p-102' },
          { kind: 'comment', id: 'c-1021' },
          { kind: 'comment', id: 'c-1071' },
        ],
      },
      {
        text: 'Đơn giao về nguội và chênh giá trên app giao đồ ăn được nhắc ở hai bài riêng biệt.',
        evidence: [
          { kind: 'post', id: 'p-104' },
          { kind: 'post', id: 'p-108' },
        ],
      },
    ],
    suggestions: [
      {
        text: 'Cân nhắc kiểm tra số nhân viên quầy giờ trưa ở chi nhánh Cầu Giấy và các chi nhánh văn phòng.',
        evidence: [
          { kind: 'post', id: 'p-101' },
          { kind: 'comment', id: 'c-1012' },
        ],
      },
      {
        text: 'Cân nhắc thử nghiệm tùy chọn cấp độ cay cho món gà hoặc sốt.',
        evidence: [
          { kind: 'post', id: 'p-103' },
          { kind: 'post', id: 'p-106' },
        ],
      },
      {
        text: 'Cân nhắc quảng bá combo mật ong trên kênh đặt hàng riêng để giảm chênh lệch giá với app giao đồ ăn.',
        evidence: [
          { kind: 'post', id: 'p-102' },
          { kind: 'post', id: 'p-104' },
        ],
      },
    ],
    model: 'Mô hình Bedrock (chưa chọn)',
  },
];
