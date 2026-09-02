const aboutBody =
  "Polifin; portföy takibini, piyasa verilerini ve yapay zeka destekli finansal içgörüleri aynı deneyimde bir araya getirir. Amacımız, karmaşık finansal bilgileri kullanıcıların daha rahat takip edebileceği açık ve düzenli bir yapıya dönüştürmektir.";

const highlights = [
  {
    index: "01",
    title: "Portföy görünümü",
    description: "Varlık dağılımını, performansı ve risk göstergelerini tek yerde anlaşılır biçimde sunar.",
  },
  {
    index: "02",
    title: "Piyasa takibi",
    description: "Endeksleri, döviz kurlarını ve öne çıkan varlıkları güncel piyasa verileriyle izlemeyi kolaylaştırır.",
  },
  {
    index: "03",
    title: "AI destekli içgörü",
    description: "Finansal verileri ve haber akışını kişisel portföy bağlamında yorumlayan bir asistan deneyimi sağlar.",
  },
];

export default function HakkimizdaPage() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black tracking-wide app-primary-text">POLİFİN HAKKINDA</p>
        <h1 className="mt-1 text-2xl font-semibold app-heading">
          Finansal kararları daha anlaşılır hale getiren kişisel asistan.
        </h1>
      </div>

      <div className="rounded-xl border app-card p-6 shadow-sm">
        <p className="max-w-3xl text-sm leading-relaxed app-muted">{aboutBody}</p>

        <div className="mt-8 grid gap-7 border-t app-border pt-7 md:grid-cols-3 md:gap-0 md:pt-8">
          {highlights.map((item) => (
            <div key={item.index} className="md:border-r md:px-7 md:first:pl-0 md:last:border-r-0 md:last:pr-0">
              <div className="text-xs font-black app-primary-text">{item.index}</div>
              <h2 className="mt-3 text-base font-semibold app-heading">{item.title}</h2>
              <p className="mt-2 text-sm leading-relaxed app-muted">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
