import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * A generic used in several places to represent a piece of data with a timestamp attached.
 *
 * @see TimestampedTupleTwo
 * @see TimestampedTupleThree
 */
public class TimestampedData<T> implements Serializable, Comparable<TimestampedData<?>> {
    private final static long serialVersionUID = 859865928593408875L;

    private final Instant timestamp;
    private final T value;


    public TimestampedData(T value, Instant timestamp) {
        this.value = value;
        this.timestamp = Objects.requireNonNull(timestamp);
    }

    public T get() {
        return value;
    }


    public Instant getTimestamp() {
        return timestamp;
    }

    public TimestampedData<T> byReplacingData(T t) {
        return new TimestampedData<>(t, getTimestamp());
    }

    public TimestampedData<T> byReplacingTimestamp(Instant timestamp) {
        return new TimestampedData<>(get(), timestamp);
    }

    @Override
    public int hashCode() {
        T v = get();
        Instant t = getTimestamp();
        long result = (v == null ? 0 : v.hashCode()) + (t == null ? 0 : t.hashCode());
        return (int) (result % Integer.MAX_VALUE);
    }

    @Override
    public boolean equals(Object o) {

        // If the object is compared with itself then return true
        if (o == this) {
            return true;
        }

        if (!(o instanceof TimestampedData)) {
            return false;
        }

        // typecast o to TimestampedData so that we can compare data members
        TimestampedData<?> other = (TimestampedData<?>) o;

        // Compare the data members and return accordingly
        return Objects.equals(get(), other.get()) &&
                Objects.equals(getTimestamp(), other.getTimestamp());
    }

    @Override
    public int compareTo(TimestampedData o) {
        return this.timestamp.compareTo(o.timestamp);
    }
}
