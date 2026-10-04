package xiaozhi.common.redis;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import jakarta.annotation.Resource;
import xiaozhi.common.utils.ResourcesUtils;

/**
 * Lớp công cụ Redis
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Component
public class RedisUtils {
    @Resource
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private ResourcesUtils resourceUtils;

    /**
     * Thời gian hết hạn mặc định là 24 giờ, đơn vị: giây
     */
    public final static long DEFAULT_EXPIRE = 60 * 60 * 24L;
    /**
     * Thời gian hết hạn là 1 giờ, đơn vị: giây
     */
    public final static long HOUR_ONE_EXPIRE = (long) 60 * 60;
    /**
     * Thời gian hết hạn là 6 giờ, đơn vị: giây
     */
    public final static long HOUR_SIX_EXPIRE = 60 * 60 * 6L;
    /**
     * Không đặt thời gian hết hạn
     */
    public final static long NOT_EXPIRE = -1L;

    public Long increment(String key, long expire) {
        Long increment = redisTemplate.opsForValue().increment(key, 1L);
        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
        return increment;
    }

    public Long increment(String key) {
        return redisTemplate.opsForValue().increment(key, 1L);
    }

    public Long decrement(String key) {
        return redisTemplate.opsForValue().decrement(key, 1L);
    }



    public void set(String key, Object value, long expire) {
        redisTemplate.opsForValue().set(key, value);
        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
    }

    public void set(String key, Object value) {
        set(key, value, DEFAULT_EXPIRE);
    }

    public Object get(String key, long expire) {
        Object value = redisTemplate.opsForValue().get(key);
        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
        return value;
    }

    public Object get(String key) {
        return get(key, NOT_EXPIRE);
    }

    public void delete(String key) {
        redisTemplate.delete(key);
    }

    public void delete(Collection<String> keys) {
        redisTemplate.delete(keys);
    }

    public Object hGet(String key, String field) {
        return redisTemplate.opsForHash().get(key, field);
    }

    public Map<String, Object> hGetAll(String key) {
        HashOperations<String, String, Object> hashOperations = redisTemplate.opsForHash();
        return hashOperations.entries(key);
    }

    public void hMSet(String key, Map<String, Object> map) {
        hMSet(key, map, DEFAULT_EXPIRE);
    }

    public void hMSet(String key, Map<String, Object> map, long expire) {
        redisTemplate.opsForHash().putAll(key, map);

        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
    }

    public void hSet(String key, String field, Object value) {
        hSet(key, field, value, DEFAULT_EXPIRE);
    }

    public void hSet(String key, String field, Object value, long expire) {
        redisTemplate.opsForHash().put(key, field, value);

        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
    }

    public void expire(String key, long expire) {
        redisTemplate.expire(key, expire, TimeUnit.SECONDS);
    }

    public void hDel(String key, Object... fields) {
        redisTemplate.opsForHash().delete(key, fields);
    }

    public void leftPush(String key, Object value) {
        leftPush(key, value, DEFAULT_EXPIRE);
    }

    public void leftPush(String key, Object value, long expire) {
        redisTemplate.opsForList().leftPush(key, value);

        if (expire != NOT_EXPIRE) {
            expire(key, expire);
        }
    }

    public Object rightPop(String key) {
        return redisTemplate.opsForList().rightPop(key);
    }


    /**
     * Xóa tất cả các khóa trong tất cả cơ sở dữ liệu Redis
     */
    public void emptyAll() {
        // Lua script FLUSHALL là lệnh redis để xóa tất cả các thư viện
        String luaScript =resourceUtils.loadString("lua/emptyAll.lua");

        // Tạo một đối tượng DefaultRedisScript
        DefaultRedisScript<Void> redisScript = new DefaultRedisScript<>();
        redisScript.setScriptText(luaScript); // Đặt nội dung tập lệnh Lua
        redisScript.setResultType(Void.class); // Đặt loại giá trị trả về

        // Thực thi tập lệnh Lua
        List<String> keys = Collections.emptyList(); // Nếu tập lệnh không dựa vào khóa, bạn có thể chuyển vào danh sách trống
        redisTemplate.execute(redisScript, keys);

    }

    /**
     * Lấy giá trị của khóa được chỉ định trong redis. Nếu giá trị trống, hãy đặt giá trị mặc định của khóa.
     * @param key phím redis
     * @param defaultValue giá trị mặc định
     * @param expiresInSecond hạnInSecond thời gian hết hạn
     * @return trả về giá trị của khóa
     */
    public String getKeyOrCreate(String key, String defaultValue,Long expiresInSecond) {
        // Tập lệnh Lua
        String luaScript = resourceUtils.loadString("lua/getKeyOrCreate.lua");

        DefaultRedisScript<String> redisScript = new DefaultRedisScript<>();
        redisScript.setScriptText(luaScript);
        redisScript.setResultType(String.class);

        // Thực thi tập lệnh Lua
        List<String> keys = Collections.singletonList(key);
        return redisTemplate.execute(redisScript, keys, defaultValue,expiresInSecond);
    }



}