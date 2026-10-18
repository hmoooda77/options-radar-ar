export const DARK_POOL_STATUS = {
  available: false,
  source: 'FINRA OTC Transparency',
  url: 'https://otctransparency.finra.org/otctransparency/',
  message: 'لا يوجد مزود Dark Pool لحظي موصول. بيانات FINRA العامة دورية/تجميعية ولا تكشف بالضرورة كل صفقة لحظية أو هوية الطرفين.'
};

export function explainEvidence(option) {
  const volume = Number(option?.volume) || 0;
  const oi = Number(option?.openInterest) || 0;
  const volOi = oi ? volume / oi : null;
  const spread = Number(option?.ask) > 0 && Number(option?.bid) >= 0
    ? (Number(option.ask) - Number(option.bid)) / Math.max((Number(option.ask) + Number(option.bid)) / 2, 0.01)
    : null;
  return {
    volOi,
    spreadPercent: spread == null ? null : spread * 100,
    liquidity: spread == null ? 'غير كافية' : spread <= 0.03 ? 'جيدة نسبيًا' : spread <= 0.08 ? 'متوسطة' : 'ضعيفة/مكلفة',
    institutional: 'غير مثبتة',
    reasons: [
      'الحجم وOpen Interest لا يكشفان هوية المتداول.',
      'التداول قرب Ask قد يشير إلى تنفيذ عدواني لكنه لا يثبت فتح مركز شراء.',
      'قد تكون الصفقة إغلاقًا أو تحوطًا أو جزءًا من استراتيجية متعددة الأرجل.'
    ]
  };
}
