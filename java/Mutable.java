import java.io.Serializable;
import java.util.function.Function;

/**
 * Useful with lambdas and other places where you need a "final" object but need to modify its value.
 */
public class Mutable<T> implements Serializable, Cloneable {

    private final static long serialVersionUID = -851453018224583257L;
    private T value;

    public Mutable() {
    }

    public Mutable(T value) {
        this.value = value;
    }

    /**
     * Returns a String.valueOf() representation of the value, threadsafe.
     */
    public synchronized String toString() {
        return String.valueOf(get());
    }

    /**
     * Gets the value, threadsafe.
     */
    public synchronized T get() {
        return value;
    }

    /**
     * Sets the value, threadsafe.
     */
    public synchronized void set(T value) {
        this.value = value;
    }

    /**
     * Gets and then Sets the value with the given function but does it in
     * a threadsafe, synchronized fashion.
     */
    public synchronized void operate(Function<T, T> func) {
        set(func.apply(get()));
    }
}
