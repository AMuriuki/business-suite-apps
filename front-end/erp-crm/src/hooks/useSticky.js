// import hooks from react
import { useEffect, useState, useRef } from "react"

function useSticky() {
    const [isSticky, setSticky] = useState(false) //define the state and set it to false
    const element = useRef(null)

    //This function is called when user starts scrolling
    const handleScroll = () => {
        //check if number of pixels the page has currently scrolled along  the vertical axis is greater than the position of the current element relative to its bottom
        window.scrollY > element.current.getBoundingClientRect().bottom 
            ? setSticky(true)
            : setSticky(false)
    }

    //This function handles the scroll performance issue
    const debounce = (func, wait = 20, immediate = true) => {
        let timeOut
        return () => {
            let context = this,
                args = arguments
            const later = () => {
                timeOut = null
                if (!immediate) func.apply(context, args)
            }
            const callNow = immediate && !timeOut
            clearTimeout(timeOut)
            timeOut = setTimeout(later, wait)
            if (callNow) func.apply(context, args)
        }
    }

    useEffect(() => {
        window.addEventListener("scroll", debounce(handleScroll))
        return () => {
            window.removeEventListener("scroll", () => handleScroll)
        }
    }, [debounce, handleScroll])

    return { isSticky, element }
}

export default useSticky