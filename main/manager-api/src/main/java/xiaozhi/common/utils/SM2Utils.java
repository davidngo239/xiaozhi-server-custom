package xiaozhi.common.utils;

import org.bouncycastle.asn1.gm.GMNamedCurves;
import org.bouncycastle.asn1.x9.X9ECParameters;
import org.bouncycastle.crypto.engines.SM2Engine;
import org.bouncycastle.crypto.params.ECDomainParameters;
import org.bouncycastle.crypto.params.ECPrivateKeyParameters;
import org.bouncycastle.crypto.params.ECPublicKeyParameters;
import org.bouncycastle.crypto.params.ParametersWithRandom;
import org.bouncycastle.jcajce.provider.asymmetric.ec.BCECPrivateKey;
import org.bouncycastle.jcajce.provider.asymmetric.ec.BCECPublicKey;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.math.ec.ECPoint;
import org.bouncycastle.util.encoders.Hex;

import java.math.BigInteger;
import java.security.*;
import java.security.spec.ECGenParameterSpec;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Lớp công cụ mã hóa SM2 (ở định dạng thập lục phân, phù hợp với dự án dịch vụ lưu trữ chanchen)
 */
public class SM2Utils {

    /**
     * Hằng số khóa công khai
     */
    public static final String KEY_PUBLIC_KEY = "publicKey";
    /**
     * Hằng số giá trị trả về của khóa riêng
     */
    public static final String KEY_PRIVATE_KEY = "privateKey";

    static {
        Security.addProvider(new BouncyCastleProvider());
    }

    /**
     * Thuật toán mã hóa SM2
     *
     * @param publicKey khóa công khai thập lục phân
     * @param data dữ liệu văn bản thuần túy
     * @return bản mã thập lục phân
     */
    public static String encrypt(String publicKey, String data) {
        try {
            // Lấy các tham số của đường cong SM2
            X9ECParameters sm2ECParameters = GMNamedCurves.getByName("sm2p256v1");
            // Xây dựng các tham số thuật toán ECC, phương trình đường cong, đường cong elip điểm G, số nguyên lớn N
            ECDomainParameters domainParameters = new ECDomainParameters(sm2ECParameters.getCurve(), sm2ECParameters.getG(), sm2ECParameters.getN());
            //Trích xuất điểm khóa công khai
            ECPoint pukPoint = sm2ECParameters.getCurve().decodePoint(Hex.decode(publicKey));
            // Số 02 hoặc 03 ở phía trước khóa chung biểu thị khóa chung được nén và 04 biểu thị khóa chung không nén. Khi 04 được sử dụng, 04 trước đó có thể được loại bỏ.
            ECPublicKeyParameters publicKeyParameters = new ECPublicKeyParameters(pukPoint, domainParameters);

            SM2Engine sm2Engine = new SM2Engine(SM2Engine.Mode.C1C3C2);
            // Đặt sm2 sang chế độ mã hóa
            sm2Engine.init(true, new ParametersWithRandom(publicKeyParameters, new SecureRandom()));

            byte[] in = data.getBytes(StandardCharsets.UTF_8);
            byte[] arrayOfBytes = sm2Engine.processBlock(in, 0, in.length);
            return Hex.toHexString(arrayOfBytes);
        } catch (Exception e) {
            throw new RuntimeException("SM2加密失败", e);
        }
    }

    /**
     * Thuật toán giải mã SM2
     *
     * @param privateKey Khóa riêng thập lục phân
     * @param cipherData Dữ liệu văn bản mã hóa thập lục phân
     * @return văn bản thuần túy
     */
    public static String decrypt(String privateKey, String cipherData) {
        try {
            // Khi sử dụng thư viện BC để mã hóa và giải mã, văn bản mã hóa bắt đầu bằng 04. Nếu không có số 04 ở phía trước văn bản mã hóa đến, hãy thêm nó vào.
            if (!cipherData.startsWith("04")) {
                cipherData = "04" + cipherData;
            }
            byte[] cipherDataByte = Hex.decode(cipherData);
            BigInteger privateKeyD = new BigInteger(privateKey, 16);
            //Lấy các tham số của đường cong SM2
            X9ECParameters sm2ECParameters = GMNamedCurves.getByName("sm2p256v1");
            //Xây dựng tham số miền
            ECDomainParameters domainParameters = new ECDomainParameters(sm2ECParameters.getCurve(), sm2ECParameters.getG(), sm2ECParameters.getN());
            ECPrivateKeyParameters privateKeyParameters = new ECPrivateKeyParameters(privateKeyD, domainParameters);

            SM2Engine sm2Engine = new SM2Engine(SM2Engine.Mode.C1C3C2);
            // Đặt sm2 sang chế độ giải mã
            sm2Engine.init(false, privateKeyParameters);

            byte[] arrayOfBytes = sm2Engine.processBlock(cipherDataByte, 0, cipherDataByte.length);
            return new String(arrayOfBytes, StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("SM2解密失败", e);
        }
    }

    /**
     * Tạo cặp khóa
     */
    public static Map<String, String> createKey() {
        try {
            ECGenParameterSpec sm2Spec = new ECGenParameterSpec("sm2p256v1");
            // Nhận trình tạo cặp khóa kiểu đường cong elip
            KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC", new BouncyCastleProvider());
            // Khởi tạo trình tạo với tham số SM2
            kpg.initialize(sm2Spec);
            // Nhận cặp khóa
            KeyPair keyPair = kpg.generateKeyPair();
            PublicKey publicKey = keyPair.getPublic();
            BCECPublicKey p = (BCECPublicKey) publicKey;
            PrivateKey privateKey = keyPair.getPrivate();
            BCECPrivateKey s = (BCECPrivateKey) privateKey;
            
            Map<String, String> result = new HashMap<>();
            result.put(KEY_PUBLIC_KEY, Hex.toHexString(p.getQ().getEncoded(false)));
            result.put(KEY_PRIVATE_KEY, Hex.toHexString(s.getD().toByteArray()));
            return result;
        } catch (Exception e) {
            throw new RuntimeException("生成SM2密钥对失败", e);
        }
    }


}