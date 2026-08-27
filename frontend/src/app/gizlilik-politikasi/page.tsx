const sections = [
  {
    title: "1. Giriş",
    body: "POLIFIN (\"biz\", \"uygulama\"), İnternTech 2026 kapsamında geliştirilen bir eğitim/demo projesidir. Bu Gizlilik Politikası, uygulamayı kullanırken hangi bilgilerin toplandığını, nasıl kullanıldığını ve kullanıcı olarak haklarınızın neler olduğunu açıklar. POLIFIN şu an bir konsept/demo çalışmasıdır; gösterilen veriler ve işlemler temsilidir, gerçek finansal işlem içermez.",
  },
  {
    title: "2. Topladığımız Bilgiler",
    body: "Uygulamaya kayıt olduğunuzda veya kullandığınızda aşağıdaki bilgileri toplayabiliriz: ad-soyad ve e-posta adresi gibi hesap bilgileri; uygulama içinde oluşturduğunuz demo portföy, hedef ve tercih verileri; uygulamayı nasıl kullandığınıza dair temel kullanım/etkileşim bilgileri (örneğin ziyaret edilen sayfalar).",
  },
  {
    title: "3. Bilgilerin Kullanım Amacı",
    body: "Topladığımız bilgileri şu amaçlarla kullanırız: hesabınızı oluşturmak ve size hizmet sunmak, uygulama deneyimini kişiselleştirmek (örneğin risk profili ve yatırım tercihleriniz), destek taleplerinize yanıt vermek, uygulamayı geliştirmek ve hataları tespit etmek.",
  },
  {
    title: "4. Çerezler (Cookies)",
    body: "Uygulama, oturumunuzu açık tutmak ve tercihlerinizi hatırlamak için temel çerezler kullanabilir. Üçüncü taraf reklam veya takip çerezleri kullanılmamaktadır.",
  },
  {
    title: "5. Bilgilerin Paylaşılması",
    body: "Kişisel bilgileriniz, yasal bir zorunluluk olmadıkça veya açık rızanız olmadan üçüncü taraflarla paylaşılmaz veya satılmaz. Uygulamanın çalışması için gerekli teknik altyapı sağlayıcılarıyla (örneğin veritabanı barındırma hizmeti) sınırlı ölçüde veri paylaşımı olabilir.",
  },
  {
    title: "6. Veri Güvenliği",
    body: "Verilerinizin güvenliğini sağlamak için makul teknik ve idari önlemler alıyoruz. Ancak internet üzerinden hiçbir veri aktarımının veya elektronik saklama yönteminin %100 güvenli olmadığını hatırlatırız.",
  },
  {
    title: "7. Kullanıcı Hakları",
    body: "6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) kapsamında; verilerinizin işlenip işlenmediğini öğrenme, işlenmişse buna ilişkin bilgi talep etme, düzeltilmesini veya silinmesini isteme haklarına sahipsiniz. Bu haklarınızı kullanmak için bizimle destek kanallarımız üzerinden iletişime geçebilirsiniz.",
  },
  {
    title: "8. Politika Değişiklikleri",
    body: "Bu Gizlilik Politikası zaman zaman güncellenebilir. Önemli değişiklikler olması durumunda uygulama üzerinden bilgilendirme yapılacaktır.",
  },
  {
    title: "9. İletişim",
    body: "Sorularınız için: destek@polifin.com veya 0850 255 20 00 üzerinden bize ulaşabilirsiniz.",
  },
];

const lastUpdated = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" }).format(
  new Date(),
);

export default function GizlilikPolitikasiPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold app-heading">POLIFIN — Gizlilik Politikası</h1>
        <p className="mt-1 text-sm app-muted">Son güncelleme: {lastUpdated}</p>
      </div>

      <div className="rounded-xl border app-card p-6 shadow-sm">
        <div className="divide-y app-border-soft">
          {sections.map((section) => (
            <section key={section.title} className="py-5 first:pt-0 last:pb-0">
              <h2 className="text-base font-semibold app-heading">{section.title}</h2>
              <p className="mt-2 text-sm leading-relaxed app-muted">{section.body}</p>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
